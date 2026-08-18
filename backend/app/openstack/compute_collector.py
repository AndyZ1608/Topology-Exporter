"""
Nova compute collector for servers.
"""
import logging
from typing import Optional
from openstack.connection import Connection

logger = logging.getLogger(__name__)


class ComputeCollector:
    """Collects compute information from Nova."""

    def __init__(self, conn: Optional[Connection] = None):
        self.conn = conn
        self._servers_cache: dict = {}

    def collect_servers(self) -> dict[str, dict]:
        """
        Collect all servers across all projects.

        Returns:
            Dict mapping server_id to normalized server data.
        """
        if not self.conn:
            logger.warning("No connection - skipping server collection")
            return {}

        try:
            servers = {}
            # Nova with admin credentials can list all servers
            for server in self.conn.compute.servers(all_tenants=True):
                servers[server.id] = self._normalize_server(server)
            self._servers_cache = servers
            logger.info(f"Collected {len(servers)} servers")
            return servers
        except Exception as exc:
            logger.error("Failed to collect servers (%s)", type(exc).__name__)
            raise

    def _normalize_server(self, server) -> dict:
        """Normalize Nova server to standard format."""
        # Extract fixed IPs
        fixed_ips = []
        mac_addresses = []

        if hasattr(server, "addresses") and server.addresses:
            for network_name, addr_list in server.addresses.items():
                for addr in addr_list:
                    if "addr" in addr:
                        fixed_ips.append(addr["addr"])
                    if "OS-EXT-IPS-MAC:mac_addr" in addr:
                        mac_addresses.append(addr["OS-EXT-IPS-MAC:mac_addr"])

        # Extract flavor info
        flavor_id = None
        flavor_name = None
        if hasattr(server, "flavor") and server.flavor:
            flavor_info = server.flavor
            if isinstance(flavor_info, dict):
                flavor_id = flavor_info.get("id")
                flavor_name = flavor_info.get("original_name", flavor_id)
            elif hasattr(flavor_info, "id"):
                flavor_id = flavor_info.id
                flavor_name = getattr(flavor_info, "name", flavor_id)

        return {
            "id": server.id,
            "name": server.name,
            "project_id": server.project_id,
            "status": server.status,
            "created_at": str(server.created_at) if server.created_at else None,
            "metadata": dict(server.metadata) if hasattr(server, "metadata") and server.metadata else {},
            "addresses": dict(server.addresses) if hasattr(server, "addresses") and server.addresses else {},
            "fixed_ips": fixed_ips,
            "mac_addresses": mac_addresses,
            "flavor_id": flavor_id,
            "flavor_name": flavor_name,
            "host": getattr(server, "host", None),
            "availability_zone": getattr(server, "availability_zone", None),
            "tags": list(server.tags) if hasattr(server, "tags") and server.tags else [],
        }

    def get_server(self, server_id: str) -> Optional[dict]:
        """Get a specific server by ID."""
        if server_id in self._servers_cache:
            return self._servers_cache[server_id]

        if not self.conn:
            return None

        try:
            server = self.conn.compute.get_server(server_id)
            if server:
                return self._normalize_server(server)
        except Exception as exc:
            logger.error(
                "Failed to get server %s (%s)", server_id, type(exc).__name__
            )
        return None

    def get_servers_by_project(self, project_id: str) -> list[dict]:
        """Get all servers for a specific project."""
        if not self._servers_cache:
            self.collect_servers()

        return [
            server for server in self._servers_cache.values()
            if server["project_id"] == project_id
        ]
