"""
Neutron network collector for networks, subnets, ports, routers, and floating IPs.
"""
import logging
from typing import Optional
from openstack.connection import Connection

logger = logging.getLogger(__name__)


class NetworkCollector:
    """Collects network information from Neutron."""

    def __init__(self, conn: Optional[Connection] = None):
        self.conn = conn
        self._networks_cache: dict = {}
        self._subnets_cache: dict = {}
        self._ports_cache: dict = {}
        self._routers_cache: dict = {}
        self._floating_ips_cache: dict = {}
        self._trunks_cache: dict = {}
        self._security_groups_cache: dict = {}

    def collect_all(self) -> dict:
        """
        Collect all network resources.

        Returns:
            Dict containing all network resources.
        """
        if not self.conn:
            logger.warning("No connection - skipping network collection")
            return {}

        try:
            self._collect_networks()
            self._collect_subnets()
            self._collect_ports()
            self._collect_routers()
            self._collect_floating_ips()
            self._collect_trunks()
            self._collect_security_groups()

            logger.info(
                f"Collected: {len(self._networks_cache)} networks, "
                f"{len(self._subnets_cache)} subnets, "
                f"{len(self._ports_cache)} ports, "
                f"{len(self._routers_cache)} routers, "
                f"{len(self._floating_ips_cache)} floating IPs"
            )

            return {
                "networks": self._networks_cache,
                "subnets": self._subnets_cache,
                "ports": self._ports_cache,
                "routers": self._routers_cache,
                "floating_ips": self._floating_ips_cache,
                "trunks": self._trunks_cache,
                "security_groups": self._security_groups_cache,
            }
        except Exception as e:
            logger.error(f"Failed to collect network resources: {e}")
            raise

    def _collect_networks(self):
        """Collect all networks."""
        for network in self.conn.network.networks():
            self._networks_cache[network.id] = {
                "id": network.id,
                "name": network.name,
                "project_id": network.project_id,
                "router:external": network.router_external,
                "provider:network_type": getattr(network, "provider:network_type", None),
                "provider:physical_network": getattr(network, "provider:physical_network", None),
                "provider:segmentation_id": getattr(network, "provider:segmentation_id", None),
                "shared": network.shared,
                "status": network.status,
                "subnets": list(network.subnets) if network.subnets else [],
                "tags": list(network.tags) if hasattr(network, "tags") and network.tags else [],
            }

    def _collect_subnets(self):
        """Collect all subnets."""
        for subnet in self.conn.network.subnets():
            self._subnets_cache[subnet.id] = {
                "id": subnet.id,
                "name": subnet.name,
                "network_id": subnet.network_id,
                "project_id": subnet.project_id,
                "cidr": subnet.cidr,
                "gateway_ip": subnet.gateway_ip,
                "ip_version": subnet.ip_version,
                "enable_dhcp": subnet.enable_dhcp,
                "dns_nameservers": list(subnet.dns_nameservers) if hasattr(subnet, "dns_nameservers") and subnet.dns_nameservers else [],
                "allocation_pools": [dict(pool) for pool in subnet.allocation_pools] if hasattr(subnet, "allocation_pools") and subnet.allocation_pools else [],
                "tags": list(subnet.tags) if hasattr(subnet, "tags") and subnet.tags else [],
            }

    def _collect_ports(self):
        """Collect all ports."""
        for port in self.conn.network.ports():
            self._ports_cache[port.id] = {
                "id": port.id,
                "name": port.name,
                "network_id": port.network_id,
                "project_id": port.project_id,
                "device_id": port.device_id,
                "device_owner": port.device_owner,
                "device_owner_category": self._categorize_device_owner(port.device_owner),
                "mac_address": port.mac_address,
                "fixed_ips": [{"ip_address": ip.get("ip_address"), "subnet_id": ip.get("subnet_id")} for ip in port.fixed_ips] if port.fixed_ips else [],
                "status": port.status,
                "binding_host_id": getattr(port, "binding_host_id", None),
                "security_groups": list(port.security_groups) if port.security_groups else [],
                "tags": list(port.tags) if hasattr(port, "tags") and port.tags else [],
            }

    def _categorize_device_owner(self, device_owner: str) -> str:
        """Categorize device owner to understand what owns the port."""
        if not device_owner:
            return "unknown"
        owner_lower = device_owner.lower()
        if "compute" in owner_lower:
            return "compute"
        if "network" in owner_lower:
            if "router" in owner_lower:
                return "router_interface"
            if "dhcp" in owner_lower:
                return "dhcp"
        if "lb" in owner_lower or "loadbalancer" in owner_lower:
            return "loadbalancer"
        if "vpn" in owner_lower:
            return "vpn"
        return "other"

    def _collect_routers(self):
        """Collect all routers."""
        for router in self.conn.network.routers():
            external_gateway = None
            if router.external_gateway_info:
                ext_gw = router.external_gateway_info
                external_gateway = {
                    "network_id": ext_gw.get("network_id"),
                    "enable_snat": ext_gw.get("enable_snat"),
                    "external_fixed_ips": ext_gw.get("external_fixed_ips", []),
                }

            self._routers_cache[router.id] = {
                "id": router.id,
                "name": router.name,
                "project_id": router.project_id,
                "status": router.status,
                "external_gateway_info": external_gateway,
                "interfaces": [],  # Will be populated from ports
            }

    def _collect_floating_ips(self):
        """Collect all floating IPs."""
        for fip in self.conn.network.ips():
            self._floating_ips_cache[fip.id] = {
                "id": fip.id,
                "floating_ip_address": fip.floating_ip_address,
                "fixed_ip_address": fip.fixed_ip_address,
                "port_id": fip.port_id,
                "router_id": fip.router_id,
                "project_id": fip.project_id,
                "status": fip.status,
                "floating_network_id": fip.floating_network_id,
            }

    def _collect_trunks(self):
        """Collect all trunks."""
        try:
            # Trunks might not be available in all OpenStack deployments
            if hasattr(self.conn.network, "trunks"):
                for trunk in self.conn.network.trunks():
                    self._trunks_cache[trunk.id] = {
                        "id": trunk.id,
                        "name": trunk.name,
                        "project_id": trunk.project_id,
                        "status": trunk.status,
                        "port_id": trunk.port_id,
                        "sub_ports": [
                            {
                                "port_id": sp.get("port_id"),
                                "segmentation_type": sp.get("segmentation_type"),
                                "segmentation_id": sp.get("segmentation_id"),
                            }
                            for sp in (trunk.sub_ports if hasattr(trunk, "sub_ports") else [])
                        ],
                    }
        except Exception as e:
            logger.warning(f"Trunk collection not available: {e}")

    def _collect_security_groups(self):
        """Collect all security groups."""
        for sg in self.conn.network.security_groups():
            self._security_groups_cache[sg.id] = {
                "id": sg.id,
                "name": sg.name,
                "project_id": sg.project_id,
                "description": sg.description,
                "rules": [
                    {
                        "id": rule.id,
                        "direction": rule.direction,
                        "protocol": rule.protocol,
                        "port_range_min": rule.port_range_min,
                        "port_range_max": rule.port_range_max,
                        "remote_ip_prefix": rule.remote_ip_prefix,
                        "remote_group_id": rule.remote_group_id,
                    }
                    for rule in (sg.rules if hasattr(sg, "rules") else [])
                ],
            }

    def link_router_interfaces(self):
        """Link router interfaces to routers based on ports."""
        for port in self._ports_cache.values():
            if port["device_owner_category"] == "router_interface":
                router_id = port["device_id"]
                if router_id in self._routers_cache:
                    self._routers_cache[router_id]["interfaces"].append({
                        "port_id": port["id"],
                        "network_id": port["network_id"],
                    })

    # Getters for cached data
    def get_networks(self) -> dict:
        return self._networks_cache

    def get_subnets(self) -> dict:
        return self._subnets_cache

    def get_ports(self) -> dict:
        return self._ports_cache

    def get_routers(self) -> dict:
        return self._routers_cache

    def get_floating_ips(self) -> dict:
        return self._floating_ips_cache

    def get_trunks(self) -> dict:
        return self._trunks_cache

    def get_security_groups(self) -> dict:
        return self._security_groups_cache
