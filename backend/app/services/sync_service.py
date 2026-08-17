"""
Topology sync service - handles background synchronization with OpenStack.
"""
import logging
import threading
import time
from datetime import datetime
from typing import Optional

from app.config import settings
from app.openstack import IdentityCollector, ComputeCollector, NetworkCollector
from app.topology.graph_builder import GraphBuilder
from app.schemas.topology import TopologyResponse, SyncStatusResponse

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
        self._sync_interval = settings.TOPOLOGY_SYNC_INTERVAL

        # Collectors
        self._identity_collector = IdentityCollector()
        self._compute_collector = ComputeCollector()
        self._network_collector = NetworkCollector()
        self._graph_builder = GraphBuilder()

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
        while not self._stop_event.is_set():
            try:
                self.sync()
            except Exception as e:
                logger.error(f"Background sync error: {e}")

            # Wait for interval or stop event
            self._stop_event.wait(timeout=self._sync_interval)

    def sync(self, force: bool = False) -> SyncStatusResponse:
        """
        Perform a topology sync.

        Args:
            force: Force sync even if already syncing

        Returns:
            Sync status
        """
        if self._sync_status.status == "syncing" and not force:
            logger.warning("Sync already in progress")
            return self._sync_status

        start_time = time.time()
        self._sync_status.status = "syncing"
        self._sync_status.failed_collectors = []

        try:
            if settings.DEMO_MODE:
                # Demo mode - use mock data
                from app.services.demo_data import get_demo_topology
                self._current_topology = get_demo_topology()
                logger.info("Demo topology loaded")
            else:
                # Real OpenStack sync
                self._sync_from_openstack()

            # Success
            duration = time.time() - start_time
            self._sync_status = SyncStatusResponse(
                status="success",
                last_sync=datetime.utcnow(),
                last_duration=duration,
                last_error=None,
                partial=False,
                failed_collectors=[],
                node_count=len(self._current_topology.nodes) if self._current_topology else 0,
                edge_count=len(self._current_topology.edges) if self._current_topology else 0,
            )
            logger.info(f"Sync completed: {self._sync_status.node_count} nodes, {self._sync_status.edge_count} edges")

        except Exception as e:
            duration = time.time() - start_time
            # Check if we have partial data
            if self._current_topology:
                self._sync_status = SyncStatusResponse(
                    status="partial",
                    last_sync=datetime.utcnow(),
                    last_duration=duration,
                    last_error=str(e),
                    partial=True,
                    failed_collectors=self._sync_status.failed_collectors,
                    node_count=len(self._current_topology.nodes),
                    edge_count=len(self._current_topology.edges),
                )
            else:
                self._sync_status = SyncStatusResponse(
                    status="failed",
                    last_sync=datetime.utcnow(),
                    last_duration=duration,
                    last_error=str(e),
                    partial=False,
                    failed_collectors=self._sync_status.failed_collectors,
                    node_count=0,
                    edge_count=0,
                )
            logger.error(f"Sync failed: {e}")

        return self._sync_status

    def _sync_from_openstack(self):
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
        partial = False

        # Collect resources with error handling
        try:
            projects = self._identity_collector.collect_projects()
        except Exception as e:
            logger.error(f"Failed to collect projects: {e}")
            failed_collectors.append("keystone")
            projects = {}
            partial = True

        try:
            servers = self._compute_collector.collect_servers()
        except Exception as e:
            logger.error(f"Failed to collect servers: {e}")
            failed_collectors.append("nova")
            servers = {}
            partial = True

        try:
            network_data = self._network_collector.collect_all()
            self._network_collector.link_router_interfaces()
        except Exception as e:
            logger.error(f"Failed to collect network resources: {e}")
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
            partial = True

        self._sync_status.failed_collectors = failed_collectors
        self._sync_status.partial = partial

        # Build topology
        self._current_topology = self._graph_builder.build_from_openstack(
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

        return self._graph_builder.find_internet_path(server_id)

    def get_node(self, node_id: str) -> Optional[dict]:
        """Get a node by ID."""
        if not self._current_topology:
            return None

        for node in self._current_topology.nodes:
            if node.id == node_id:
                return node.model_dump()
        return None

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
                if n.project_id is None or n.project_id in project_id_set
            ]

        # Filter by resource type
        if resource_types:
            type_set = set(resource_types)
            nodes = [n for n in nodes if n.resource_type in type_set]

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
                or any(search_lower in ip for ip in n.properties.ips)
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
