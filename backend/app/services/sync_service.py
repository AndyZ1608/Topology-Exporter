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
        except Exception as exc:
            logger.warning("Could not load topology cache (%s)", type(exc).__name__)
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
            except Exception as exc:
                logger.error("Background sync error (%s)", type(exc).__name__)

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
                from app.services.demo_data import get_demo_topology
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
                except Exception as exc:
                    # Cache availability must not change the discovered cloud state.
                    logger.warning("Could not persist topology cache (%s)", type(exc).__name__)

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
            logger.error("Sync failed (%s)", type(exc).__name__)

        finally:
            self._sync_lock.release()

        return self._sync_status

    def _sync_from_openstack(self) -> tuple[TopologyResponse, list[str]]:
        """Sync topology from OpenStack APIs."""
        from app.openstack.connection import connection_manager

        conn = connection_manager.get_connection()
        if not conn:
            raise RuntimeError("No OpenStack connection available")

        # Update collectors with connection
        self._identity_collector = IdentityCollector(conn)
        self._compute_collector = ComputeCollector(conn)
        self._network_collector = NetworkCollector(conn)

        failed_collectors = []
        # Collect resources with error handling
        try:
            projects = self._identity_collector.collect_projects()
        except Exception as exc:
            logger.error("Failed to collect projects (%s)", type(exc).__name__)
            failed_collectors.append("keystone")
            projects = {}

        try:
            servers = self._compute_collector.collect_servers()
        except Exception as exc:
            logger.error("Failed to collect servers (%s)", type(exc).__name__)
            failed_collectors.append("nova")
            servers = {}

        try:
            network_data = self._network_collector.collect_all()
            self._network_collector.link_router_interfaces()
        except Exception as exc:
            logger.error("Failed to collect network resources (%s)", type(exc).__name__)
            failed_collectors.append("neutron")
            network_data = {
                "networks": {},
                "subnets": {},
                "ports": {},
                "routers": {},
                "floating_ips": {},
                "trunks": {},
                "security_groups": {},
            }

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
        logger.info(
            "Resources discovered projects=%s servers=%s ports=%s networks=%s "
            "subnets=%s routers=%s floating_ips=%s trunks=%s",
            len(projects),
            len(servers),
            len(network_data.get("ports", {})),
            len(network_data.get("networks", {})),
            len(network_data.get("subnets", {})),
            len(network_data.get("routers", {})),
            len(network_data.get("floating_ips", {})),
            len(network_data.get("trunks", {})),
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
        projects = {node.project_id for node in nodes if node.project_id}
        floating_ips = {
            address
            for node in nodes
            for address in node.properties.floating_ips
        }
        return {
            "projects": len(projects),
            "servers": sum(node.resource_type == "server" for node in nodes),
            "networks": sum(node.resource_type == "network" for node in nodes),
            "subnets": sum(node.resource_type == "subnet" for node in nodes),
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

    def search(self, query: str) -> list[dict]:
        """Search normalized names, UUIDs, projects, IPs, and subnet CIDRs."""
        if not self._current_topology:
            return []
        needle = query.strip().lower()
        if not needle:
            return []

        matches = []
        for node in self._current_topology.nodes:
            searchable = [
                node.id,
                node.resource_id,
                node.name,
                node.project_id or "",
                node.project_name or "",
                node.properties.cidr or "",
                node.properties.gateway_ip or "",
                *node.properties.ips,
                *node.properties.floating_ips,
                *node.properties.mac_addresses,
            ]
            if any(needle in value.lower() for value in searchable):
                matches.append(node.model_dump())
        return matches

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
            nodes = [
                n for n in nodes
                if n.project_id is None
                or n.project_id in project_id_set
                or n.properties.is_shared
                or n.properties.is_external
            ]

        # Filter by resource type
        if resource_types:
            type_set = set(resource_types)
            nodes = [
                n for n in nodes
                if n.resource_type in type_set or n.role in type_set
            ]

        # Filter by status
        if status:
            nodes = [n for n in nodes if n.status.upper() == status.upper()]

        # Filter by search
        if search:
            search_lower = search.lower()
            nodes = [
                n for n in nodes
                if search_lower in n.name.lower()
                or search_lower in n.resource_id.lower()
                or (n.project_name and search_lower in n.project_name.lower())
                or any(search_lower in ip.lower() for ip in n.properties.ips)
                or any(search_lower in ip.lower() for ip in n.properties.floating_ips)
                or (n.properties.cidr and search_lower in n.properties.cidr.lower())
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
                "view": view,
            },
        }


# Global sync service
sync_service = TopologySyncService()


def get_sync_service() -> TopologySyncService:
    """Get the sync service instance."""
    return sync_service
