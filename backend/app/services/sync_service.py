"""
Topology sync service - handles background synchronization with OpenStack.
"""
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from app.config import settings
from app.openstack import IdentityCollector, ComputeCollector, NetworkCollector
from app.topology.graph_builder import GraphBuilder
from app.topology.path_engine import PathEngine
from app.schemas.topology import TopologyResponse, SyncStatusResponse
from app.repositories import SnapshotRepository

logger = logging.getLogger(__name__)


class TopologySyncService:
    """
    Manages topology synchronization with OpenStack.

    Handles:
    - Background periodic sync
    - Manual sync triggers
    - Error handling and partial sync
    - Caching previous valid topology
    """

    def __init__(self):
        self._current_topology: Optional[TopologyResponse] = None
        self._selectable_projects: dict[str, dict] = {}
        self._sync_status: SyncStatusResponse = SyncStatusResponse(status="idle")
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._sync_lock = threading.Lock()
        self._sync_interval = settings.TOPOLOGY_SYNC_INTERVAL

        # Collectors
        self._identity_collector = IdentityCollector()
        self._compute_collector = ComputeCollector()
        self._network_collector = NetworkCollector()
        self._graph_builder = GraphBuilder()
        self._path_engine = PathEngine()
        self._snapshot_repository = SnapshotRepository(settings.DATABASE_URL)

    def restore_cached_snapshot(self) -> bool:
        """Restore the latest non-authoritative snapshot if the cache is available."""
        try:
            topology = self._snapshot_repository.load_latest()
        except Exception:
            logger.exception("Could not load topology cache")
            return False
        if topology is None:
            return False
        self._current_topology = topology
        self._path_engine.set_topology(topology.nodes, topology.edges)
        logger.info(
            "Cached topology restored nodes=%s edges=%s discovered_at=%s",
            len(topology.nodes),
            len(topology.edges),
            topology.timestamp.isoformat(),
        )
        return True

    @property
    def current_topology(self) -> Optional[TopologyResponse]:
        """Get the current cached topology."""
        return self._current_topology

    @property
    def sync_status(self) -> SyncStatusResponse:
        """Get current sync status."""
        return self._sync_status

    def get_selectable_projects(self) -> list[dict]:
        """Return only validated Keystone projects from the topology domain."""
        return sorted(
            (
                {**project, "name": project.get("name") or project["id"]}
                for project in self._selectable_projects.values()
            ),
            key=lambda project: project["name"].lower(),
        )

    def get_selectable_project(self, project_id: str) -> Optional[dict]:
        project = self._selectable_projects.get(project_id)
        return dict(project) if project else None

    def start_background_sync(self):
        """Start background synchronization thread."""
        if self._sync_thread and self._sync_thread.is_alive():
            logger.warning("Background sync already running")
            return

        self._stop_event.clear()
        self._sync_thread = threading.Thread(
            target=self._background_sync_loop,
            daemon=True,
            name="topology-sync",
        )
        self._sync_thread.start()
        logger.info(f"Started background sync with interval {self._sync_interval}s")

    def stop_background_sync(self):
        """Stop background synchronization."""
        self._stop_event.set()
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
            self._sync_thread = None
        logger.info("Stopped background sync")

    def _background_sync_loop(self):
        """Background sync loop."""
        # The application lifespan performs the initial sync. Waiting first keeps
        # startup deterministic and prevents two collectors mutating one graph.
        while not self._stop_event.wait(timeout=self._sync_interval):
            try:
                self.sync()
            except Exception:
                logger.exception("Background sync error")

    def sync(self, force: bool = False) -> SyncStatusResponse:
        """
        Perform a topology sync.

        Args:
            force: Force sync even if already syncing

        Returns:
            Sync status
        """
        acquired = self._sync_lock.acquire(blocking=force)
        if not acquired:
            logger.warning("Sync already in progress")
            return self._sync_status

        start_time = time.time()
        logger.info("Discovery started")
        self._sync_status.status = "syncing"
        self._sync_status.failed_collectors = []

        try:
            failed_collectors: list[str] = []
            if settings.DEMO_MODE:
                # Demo mode - use mock data
                from app.services.demo_data import get_demo_projects, get_demo_topology
                self._selectable_projects = get_demo_projects()
                self._current_topology = get_demo_topology()
                logger.info("Demo topology loaded")
            else:
                # Real OpenStack sync
                candidate_topology, failed_collectors = self._sync_from_openstack()
                # Preserve the last complete snapshot when a later collection is
                # partial. On first boot, a partial graph is still more useful
                # than no topology at all.
                if not failed_collectors or self._current_topology is None:
                    self._current_topology = candidate_topology

            if self._current_topology:
                self._path_engine.set_topology(
                    self._current_topology.nodes,
                    self._current_topology.edges,
                )

                try:
                    self._snapshot_repository.save(
                        self._current_topology,
                        status="partial" if failed_collectors else "success",
                    )
                except Exception:
                    # Cache availability must not change the discovered cloud state.
                    logger.exception("Could not persist topology cache")

            duration = time.time() - start_time
            partial = bool(failed_collectors)
            self._sync_status = SyncStatusResponse(
                status="partial" if partial else "success",
                last_sync=datetime.now(timezone.utc),
                last_duration=duration,
                last_error=(
                    f"Collectors failed: {', '.join(failed_collectors)}"
                    if partial
                    else None
                ),
                partial=partial,
                failed_collectors=failed_collectors,
                node_count=len(self._current_topology.nodes) if self._current_topology else 0,
                edge_count=len(self._current_topology.edges) if self._current_topology else 0,
            )
            logger.info(
                "Discovery completed nodes=%s edges=%s duration_seconds=%.3f%s",
                self._sync_status.node_count,
                self._sync_status.edge_count,
                duration,
                f" (partial: {', '.join(failed_collectors)})" if partial else "",
            )

        except Exception as exc:
            duration = time.time() - start_time
            safe_error = f"Topology sync failed ({type(exc).__name__})"
            # Check if we have partial data
            if self._current_topology:
                self._sync_status = SyncStatusResponse(
                    status="partial",
                    last_sync=datetime.now(timezone.utc),
                    last_duration=duration,
                    last_error=safe_error,
                    partial=True,
                    failed_collectors=self._sync_status.failed_collectors,
                    node_count=len(self._current_topology.nodes),
                    edge_count=len(self._current_topology.edges),
                )
            else:
                self._sync_status = SyncStatusResponse(
                    status="failed",
                    last_sync=datetime.now(timezone.utc),
                    last_duration=duration,
                    last_error=safe_error,
                    partial=False,
                    failed_collectors=self._sync_status.failed_collectors,
                    node_count=0,
                    edge_count=0,
                )
            logger.exception("Sync failed")

        finally:
            self._sync_lock.release()

        return self._sync_status

    def _sync_from_openstack(self) -> tuple[TopologyResponse, list[str]]:
        """Discover projects with Keystone, then resources with project tokens."""
        from app.openstack.connection import connection_manager

        logger.info("System discovery started")
        system_connection = connection_manager.get_system_connection()
        if not system_connection:
            raise RuntimeError("No system-scoped OpenStack connection available")

        self._identity_collector = IdentityCollector(system_connection)
        failed_collectors: list[str] = []
        try:
            domain = self._identity_collector.find_domain(settings.TOPOLOGY_DOMAIN_NAME)
            logger.info(
                "Topology domain: name=%s id=%s",
                settings.TOPOLOGY_DOMAIN_NAME,
                domain["id"],
            )
            if domain["id"] != settings.TOPOLOGY_DOMAIN_ID:
                raise RuntimeError(
                    "Topology domain ID mismatch for "
                    f"{settings.TOPOLOGY_DOMAIN_NAME}: expected "
                    f"{settings.TOPOLOGY_DOMAIN_ID}, discovered {domain['id']}"
                )

            discovered_projects = self._identity_collector.collect_projects()
            logger.info("Projects returned by Keystone=%s", len(discovered_projects))
            projects = {
                project_id: project
                for project_id, project in discovered_projects.items()
                if project.get("enabled", True)
                and project.get("domain_id") == settings.TOPOLOGY_DOMAIN_ID
            }
            if any(
                project.get("domain_id") != settings.TOPOLOGY_DOMAIN_ID
                for project in projects.values()
            ):
                raise RuntimeError("Selectable project escaped topology domain validation")
            self._selectable_projects = {
                project_id: dict(project)
                for project_id, project in projects.items()
            }
            logger.info("MBFS projects=%s", len(projects))
        except Exception:
            logger.exception(
                "System discovery failed domain=%s", settings.TOPOLOGY_DOMAIN_NAME
            )
            failed_collectors.append("keystone")
            projects = {}

        servers: dict = {}
        network_data = {
            "networks": {},
            "subnets": {},
            "ports": {},
            "routers": {},
            "floating_ips": {},
            "trunks": {},
            "security_groups": {},
        }

        for project in projects.values():
            project_name = project["name"]
            project_id = project["id"]
            logger.info(
                "Project discovery started project=%s id=%s",
                project_name,
                project_id,
            )
            project_servers: dict = {}
            project_network_data = {
                key: {} for key in network_data
            }
            try:
                project_connection = connection_manager.get_project_connection(project)
            except Exception:
                logger.exception(
                    "Project authentication failed project=%s id=%s",
                    project_name,
                    project_id,
                )
                failed_collectors.append(f"auth:{project_id}")
                logger.info(
                    "servers=0 networks=0 subnets=0 ports=0 routers=0 "
                    "floating_ips=0 trunks=0"
                )
                logger.info(
                    "Project discovery completed project=%s id=%s status=failed",
                    project_name,
                    project_id,
                )
                continue

            self._compute_collector = ComputeCollector(project_connection)
            try:
                project_servers = self._compute_collector.collect_servers()
                servers.update(project_servers)
            except Exception:
                logger.exception(
                    "Nova discovery failed project=%s id=%s",
                    project_name,
                    project_id,
                )
                failed_collectors.append(f"nova:{project_id}")

            self._network_collector = NetworkCollector(project_connection)
            try:
                project_network_data = self._network_collector.collect_all()
            except Exception:
                # Individual Neutron API calls are already isolated inside the
                # collector. This guard keeps an unexpected normalization bug
                # in one project from stopping discovery of later projects.
                logger.exception(
                    "Neutron discovery failed project=%s id=%s",
                    project_name,
                    project_id,
                )
                failed_collectors.append(f"neutron:{project_id}")
            for resource_name in network_data:
                network_data[resource_name].update(
                    project_network_data.get(resource_name, {})
                )
            for resource_name in project_network_data.get("failed_resources", []):
                failed_collectors.append(f"neutron.{resource_name}:{project_id}")

            logger.info(
                "servers=%s networks=%s subnets=%s ports=%s routers=%s "
                "floating_ips=%s trunks=%s",
                len(project_servers),
                len(project_network_data.get("networks", {})),
                len(project_network_data.get("subnets", {})),
                len(project_network_data.get("ports", {})),
                len(project_network_data.get("routers", {})),
                len(project_network_data.get("floating_ips", {})),
                len(project_network_data.get("trunks", {})),
            )
            logger.info(
                "Project discovery completed project=%s id=%s",
                project_name,
                project_id,
            )

        # Build topology
        topology = self._graph_builder.build_from_openstack(
            projects=projects,
            servers=servers,
            networks=network_data.get("networks", {}),
            subnets=network_data.get("subnets", {}),
            ports=network_data.get("ports", {}),
            routers=network_data.get("routers", {}),
            floating_ips=network_data.get("floating_ips", {}),
            trunks=network_data.get("trunks", {}),
            security_groups=network_data.get("security_groups", {}),
        )
        return topology, failed_collectors

    def find_internet_path(self, server_id: str) -> dict:
        """Find internet path for a server."""
        if not self._current_topology:
            return {
                "found": False,
                "reason": "No topology available",
                "confidence": 0.0,
                "path": [],
                "inferred": False,
                "path_nodes": [],
            }

        return self._path_engine.find_internet_path(server_id).model_dump()

    def get_node(self, node_id: str) -> Optional[dict]:
        """Get a node by ID."""
        if not self._current_topology:
            return None

        for node in self._current_topology.nodes:
            if node.id == node_id:
                return node.model_dump()
        return None

    def get_resource(self, resource_type: str, resource_id: str) -> Optional[dict]:
        """Return a normalized resource without exposing an SDK object."""
        if not self._current_topology:
            return None
        for node in self._current_topology.nodes:
            if node.resource_type == resource_type and node.resource_id == resource_id:
                return self.get_node(node.id)
        return None

    def get_cloud_summary(self) -> dict:
        """Return operational inventory totals from the current snapshot."""
        nodes = self._current_topology.nodes if self._current_topology else []
        floating_ips = {
            address
            for node in nodes
            for address in node.properties.floating_ips
        }
        return {
            "projects": len(self._selectable_projects),
            "servers": sum(node.resource_type == "server" for node in nodes),
            "networks": sum(node.resource_type == "network" for node in nodes),
            "subnets": int(
                self._current_topology.metadata.get("subnets", 0)
                if self._current_topology
                else 0
            ),
            "routers": sum(node.resource_type == "router" for node in nodes),
            "floating_ips": len(floating_ips),
            "last_sync": (
                self._sync_status.last_sync.isoformat()
                if self._sync_status.last_sync
                else None
            ),
            "sync_status": self._sync_status.status,
            "partial": self._sync_status.partial,
        }

    @staticmethod
    def _searchable_values(node) -> list[str]:
        external_gateway = node.properties.external_gateway or {}
        interface_values = [
                str(value)
                for interface in node.properties.interfaces.values()
                for value in (
                    interface.get("network_id"),
                    interface.get("network_name"),
                    *(interface.get("ip_addresses") or []),
                    *(
                        nested
                        for subnet in (interface.get("subnets") or [])
                        for nested in (
                            subnet.get("id"), subnet.get("name"), subnet.get("cidr")
                        )
                    ),
                )
                if value
            ]
        router_interface_values = [
                str(value)
                for interface in node.properties.router_interfaces
                for value in (
                    interface.get("network_id"),
                    interface.get("network_name"),
                    interface.get("subnet_id"),
                    interface.get("subnet_name"),
                    interface.get("subnet_cidr"),
                    interface.get("ip_address"),
                )
                if value
            ]
        return [
            node.id, node.resource_id, node.name, node.project_id or "",
            node.project_name or "", node.properties.cidr or "",
            node.properties.gateway_ip or "", *node.properties.ips,
            *node.properties.floating_ips, *node.properties.mac_addresses,
            str(external_gateway.get("network_id") or ""),
            str(external_gateway.get("network_name") or ""),
            str(external_gateway.get("subnet_id") or ""),
            str(external_gateway.get("subnet_name") or ""),
            str(external_gateway.get("subnet_cidr") or ""),
            str(external_gateway.get("ip_address") or ""),
            *interface_values, *router_interface_values,
        ]

    def search(self, query: str) -> list[dict]:
        """Search normalized names, UUIDs, projects, IPs, and subnet CIDRs."""
        if not self._current_topology:
            return []
        needle = query.strip().lower()
        if not needle:
            return []
        return [
            node.model_dump()
            for node in self._current_topology.nodes
            if any(needle in value.lower() for value in self._searchable_values(node))
        ]

    def get_topology(
        self,
        project_ids: list[str] = None,
        resource_types: list[str] = None,
        status: str = None,
        search: str = None,
        view: str = "traffic",
    ) -> dict:
        """Get filtered topology."""
        if not self._current_topology:
            return {"nodes": [], "edges": [], "metadata": {"filtered": True, "reason": "No topology available"}}

        nodes = self._current_topology.nodes
        edges = self._current_topology.edges

        # Filter by project
        if project_ids:
            project_id_set = set(project_ids)
            node_by_id = {node.id: node for node in nodes}
            included_ids = {
                node.id for node in nodes if node.project_id in project_id_set
            }

            # Pull in only shared/external dependencies that are connected to
            # the selected project's real resources. Never include VMs from an
            # unrelated project merely because they share a network.
            changed = True
            while changed:
                changed = False
                for edge in edges:
                    for known_id, candidate_id in (
                        (edge.source, edge.target),
                        (edge.target, edge.source),
                    ):
                        candidate = node_by_id.get(candidate_id)
                        if known_id not in included_ids or candidate is None:
                            continue
                        is_dependency = (
                            candidate.resource_type == "internet"
                            or (
                                candidate.resource_type == "network"
                                and (
                                    candidate.properties.is_shared
                                    or candidate.properties.is_external
                                    or candidate.project_id is None
                                )
                            )
                        )
                        if is_dependency and candidate_id not in included_ids:
                            included_ids.add(candidate_id)
                            changed = True

            nodes = [node for node in nodes if node.id in included_ids]

        # Filter by resource type
        if resource_types:
            type_set = set(resource_types)
            nodes = [
                n for n in nodes
                if n.resource_type in type_set or n.role in type_set
            ]

        # Filter by status
        if status:
            nodes = [
                node
                for node in nodes
                if node.resource_type != "server"
                or node.status.upper() == status.upper()
            ]

        # Filter by search
        matched_node_ids = []
        if search:
            search_lower = search.lower()
            matched_node_ids = [
                node.id
                for node in nodes
                if any(
                    search_lower in value.lower()
                    for value in self._searchable_values(node)
                )
            ]

        # Get edges between remaining nodes
        node_ids = {n.id for n in nodes}
        edges = [
            e for e in edges
            if e.source in node_ids and e.target in node_ids
        ]

        return {
            "nodes": [n.model_dump() for n in nodes],
            "edges": [e.model_dump() for e in edges],
            "metadata": {
                "filtered": True,
                "original_node_count": len(self._current_topology.nodes),
                "original_edge_count": len(self._current_topology.edges),
                "view": "traffic",
                "matched_node_ids": matched_node_ids,
            },
        }


# Global sync service
sync_service = TopologySyncService()


def get_sync_service() -> TopologySyncService:
    """Get the sync service instance."""
    return sync_service
