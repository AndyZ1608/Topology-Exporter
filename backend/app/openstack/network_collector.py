"""Project-scoped Neutron resource collector."""

import logging
from collections.abc import Callable
from typing import Optional

from openstack.connection import Connection

logger = logging.getLogger(__name__)


class NetworkCollector:
    """Collect Neutron resources independently within one project scope."""

    def __init__(self, conn: Optional[Connection] = None):
        self.conn = conn
        self._reset_caches()

    def _reset_caches(self):
        self._networks_cache: dict = {}
        self._subnets_cache: dict = {}
        self._ports_cache: dict = {}
        self._routers_cache: dict = {}
        self._floating_ips_cache: dict = {}
        self._trunks_cache: dict = {}
        self._security_groups_cache: dict = {}

    @staticmethod
    def _resource_value(resource, *names, default=None):
        """Read SDK attributes across openstacksdk/Neutron naming variants."""
        for name in names:
            value = getattr(resource, name, None)
            if value is not None:
                return value
            try:
                value = resource.get(name)
            except (AttributeError, TypeError):
                value = None
            if value is not None:
                return value
        return default

    @staticmethod
    def _item_value(item, name, default=None):
        if isinstance(item, dict):
            return item.get(name, default)
        return getattr(item, name, default)

    def _collect_resource(
        self,
        resource_name: str,
        collector: Callable[[], None],
        failures: list[str],
    ) -> None:
        try:
            collector()
        except Exception:
            failures.append(resource_name)
            logger.exception("Failed to collect Neutron resource=%s", resource_name)

    def collect_all(self) -> dict:
        """Collect each resource independently so one API failure is isolated."""
        if not self.conn:
            logger.warning("No project-scoped connection - skipping network collection")
            return self._result(["connection"])

        self._reset_caches()
        failures: list[str] = []
        collectors = (
            ("networks", self._collect_networks),
            ("subnets", self._collect_subnets),
            ("ports", self._collect_ports),
            ("routers", self._collect_routers),
            ("floating_ips", self._collect_floating_ips),
            ("trunks", self._collect_trunks),
            ("security_groups", self._collect_security_groups),
        )
        for resource_name, collector in collectors:
            self._collect_resource(resource_name, collector, failures)

        self.link_router_interfaces()
        return self._result(failures)

    def _result(self, failures: list[str]) -> dict:
        return {
            "networks": self._networks_cache,
            "subnets": self._subnets_cache,
            "ports": self._ports_cache,
            "routers": self._routers_cache,
            "floating_ips": self._floating_ips_cache,
            "trunks": self._trunks_cache,
            "security_groups": self._security_groups_cache,
            "failed_resources": failures,
        }

    def _collect_networks(self):
        for network in self.conn.network.networks():
            network_id = self._resource_value(network, "id")
            self._networks_cache[network_id] = {
                "id": network_id,
                "name": self._resource_value(network, "name", default=network_id),
                "project_id": self._resource_value(network, "project_id", "tenant_id"),
                "router:external": bool(self._resource_value(
                    network, "is_router_external", "router_external", "router:external", default=False
                )),
                "provider:network_type": self._resource_value(
                    network, "provider_network_type", "provider:network_type"
                ),
                "provider:physical_network": self._resource_value(
                    network, "provider_physical_network", "provider:physical_network"
                ),
                "provider:segmentation_id": self._resource_value(
                    network, "provider_segmentation_id", "provider:segmentation_id"
                ),
                "shared": bool(self._resource_value(network, "is_shared", "shared", default=False)),
                "status": self._resource_value(network, "status", default="UNKNOWN"),
                "subnets": list(self._resource_value(network, "subnet_ids", "subnets", default=[]) or []),
                "tags": list(self._resource_value(network, "tags", default=[]) or []),
            }

    def _collect_subnets(self):
        for subnet in self.conn.network.subnets():
            subnet_id = self._resource_value(subnet, "id")
            pools = self._resource_value(subnet, "allocation_pools", default=[]) or []
            self._subnets_cache[subnet_id] = {
                "id": subnet_id,
                "name": self._resource_value(subnet, "name", default=subnet_id),
                "network_id": self._resource_value(subnet, "network_id"),
                "project_id": self._resource_value(subnet, "project_id", "tenant_id"),
                "cidr": self._resource_value(subnet, "cidr"),
                "gateway_ip": self._resource_value(subnet, "gateway_ip"),
                "ip_version": self._resource_value(subnet, "ip_version"),
                "enable_dhcp": self._resource_value(subnet, "is_dhcp_enabled", "enable_dhcp"),
                "dns_nameservers": list(self._resource_value(subnet, "dns_nameservers", default=[]) or []),
                "allocation_pools": [dict(pool) for pool in pools],
                "tags": list(self._resource_value(subnet, "tags", default=[]) or []),
            }

    def _collect_ports(self):
        for port in self.conn.network.ports():
            port_id = self._resource_value(port, "id")
            fixed_ips = self._resource_value(port, "fixed_ips", default=[]) or []
            device_owner = self._resource_value(port, "device_owner", default="")
            self._ports_cache[port_id] = {
                "id": port_id,
                "name": self._resource_value(port, "name", default=port_id),
                "network_id": self._resource_value(port, "network_id"),
                "project_id": self._resource_value(port, "project_id", "tenant_id"),
                "device_id": self._resource_value(port, "device_id", default=""),
                "device_owner": device_owner,
                "device_owner_category": self._categorize_device_owner(device_owner),
                "mac_address": self._resource_value(port, "mac_address"),
                "fixed_ips": [
                    {
                        "ip_address": self._item_value(ip, "ip_address"),
                        "subnet_id": self._item_value(ip, "subnet_id"),
                    }
                    for ip in fixed_ips
                ],
                "status": self._resource_value(port, "status", default="UNKNOWN"),
                "binding_host_id": self._resource_value(port, "binding_host_id", "binding:host_id"),
                "security_groups": list(self._resource_value(port, "security_group_ids", "security_groups", default=[]) or []),
                "tags": list(self._resource_value(port, "tags", default=[]) or []),
            }

    @staticmethod
    def _categorize_device_owner(device_owner: str) -> str:
        owner_lower = (device_owner or "").lower()
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
        return "unknown" if not owner_lower else "other"

    def _collect_routers(self):
        for router in self.conn.network.routers():
            router_id = self._resource_value(router, "id")
            ext_gw = self._resource_value(router, "external_gateway_info") or {}
            external_gateway = None
            if ext_gw:
                external_gateway = {
                    "network_id": self._item_value(ext_gw, "network_id"),
                    "enable_snat": self._item_value(ext_gw, "enable_snat"),
                    "external_fixed_ips": self._item_value(ext_gw, "external_fixed_ips", []),
                }
            self._routers_cache[router_id] = {
                "id": router_id,
                "name": self._resource_value(router, "name", default=router_id),
                "project_id": self._resource_value(router, "project_id", "tenant_id"),
                "status": self._resource_value(router, "status", default="UNKNOWN"),
                "external_gateway_info": external_gateway,
                "interfaces": [],
            }

    def _collect_floating_ips(self):
        for fip in self.conn.network.ips():
            fip_id = self._resource_value(fip, "id")
            self._floating_ips_cache[fip_id] = {
                "id": fip_id,
                "floating_ip_address": self._resource_value(fip, "floating_ip_address"),
                "fixed_ip_address": self._resource_value(fip, "fixed_ip_address"),
                "port_id": self._resource_value(fip, "port_id"),
                "router_id": self._resource_value(fip, "router_id"),
                "project_id": self._resource_value(fip, "project_id", "tenant_id"),
                "status": self._resource_value(fip, "status", default="UNKNOWN"),
                "floating_network_id": self._resource_value(fip, "floating_network_id"),
            }

    def _collect_trunks(self):
        trunks_method = getattr(self.conn.network, "trunks", None)
        if not callable(trunks_method):
            raise AttributeError("Installed openstacksdk network proxy has no trunks() method")
        for trunk in trunks_method():
            trunk_id = self._resource_value(trunk, "id")
            sub_ports = self._resource_value(trunk, "sub_ports", default=[]) or []
            self._trunks_cache[trunk_id] = {
                "id": trunk_id,
                "name": self._resource_value(trunk, "name", default=trunk_id),
                "project_id": self._resource_value(trunk, "project_id", "tenant_id"),
                "status": self._resource_value(trunk, "status", default="UNKNOWN"),
                "port_id": self._resource_value(trunk, "port_id"),
                "sub_ports": [
                    {
                        "port_id": self._item_value(sub_port, "port_id"),
                        "segmentation_type": self._item_value(sub_port, "segmentation_type"),
                        "segmentation_id": self._item_value(sub_port, "segmentation_id"),
                    }
                    for sub_port in sub_ports
                ],
            }

    def _collect_security_groups(self):
        for security_group in self.conn.network.security_groups():
            group_id = self._resource_value(security_group, "id")
            rules = self._resource_value(security_group, "security_group_rules", "rules", default=[]) or []
            self._security_groups_cache[group_id] = {
                "id": group_id,
                "name": self._resource_value(security_group, "name", default=group_id),
                "project_id": self._resource_value(security_group, "project_id", "tenant_id"),
                "description": self._resource_value(security_group, "description"),
                "rules": [
                    {
                        "id": self._item_value(rule, "id"),
                        "direction": self._item_value(rule, "direction"),
                        "protocol": self._item_value(rule, "protocol"),
                        "port_range_min": self._item_value(rule, "port_range_min"),
                        "port_range_max": self._item_value(rule, "port_range_max"),
                        "remote_ip_prefix": self._item_value(rule, "remote_ip_prefix"),
                        "remote_group_id": self._item_value(rule, "remote_group_id"),
                    }
                    for rule in rules
                ],
            }

    def link_router_interfaces(self):
        for port in self._ports_cache.values():
            if port["device_owner_category"] == "router_interface":
                router = self._routers_cache.get(port["device_id"])
                if router is not None:
                    router["interfaces"].append({
                        "port_id": port["id"],
                        "network_id": port["network_id"],
                    })

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
