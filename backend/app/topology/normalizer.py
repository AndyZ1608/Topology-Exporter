"""
Topology normalizer - converts OpenStack resources to normalized topology nodes.
"""
import logging
from typing import Optional
from app.schemas.topology import TopologyNode, NodeProperties

logger = logging.getLogger(__name__)


class TopologyNormalizer:
    """Normalizes OpenStack resources to topology nodes."""

    def __init__(self):
        self._project_names: dict[str, str] = {}

    def set_project_names(self, project_names: dict[str, str]):
        """Set project ID to name mapping."""
        self._project_names = project_names

    def get_project_name(self, project_id: Optional[str]) -> Optional[str]:
        """Get project name from ID."""
        if not project_id:
            return None
        return self._project_names.get(project_id, project_id)

    def normalize_server(
        self,
        server: dict,
        ports: list[dict],
        floating_ips: list[str] = None,
    ) -> TopologyNode:
        """Normalize a Nova server to a topology node."""
        fixed_ips = []
        mac_addresses = []

        for port in ports:
            for fixed_ip in port.get("fixed_ips", []):
                if fixed_ip.get("ip_address"):
                    fixed_ips.append(fixed_ip["ip_address"])
            if port.get("mac_address"):
                mac_addresses.append(port["mac_address"])

        properties = NodeProperties(
            ips=fixed_ips,
            mac_addresses=mac_addresses,
            flavor=server.get("flavor_name"),
            metadata=server.get("metadata", {}),
            floating_ips=floating_ips or [],
        )

        return TopologyNode(
            id=f"server:{server['id']}",
            resource_id=server["id"],
            resource_type="server",
            role="vm",  # Default role, will be updated by classifier
            name=server["name"],
            project_id=server.get("project_id"),
            project_name=self.get_project_name(server.get("project_id")),
            status=server.get("status", "UNKNOWN"),
            layer="workload",
            properties=properties,
            tags=server.get("tags", []),
        )

    def normalize_network(self, network: dict, subnets: list[dict] = None) -> TopologyNode:
        """Normalize a Neutron network to a topology node."""
        cidrs = []
        gateway_ips = []

        for subnet in (subnets or []):
            if subnet.get("cidr"):
                cidrs.append(subnet["cidr"])
            if subnet.get("gateway_ip"):
                gateway_ips.append(subnet["gateway_ip"])

        is_external = network.get("router:external", False)

        # Determine layer based on network type
        layer = "network"
        if is_external:
            layer = "external"
        elif network.get("provider:physical_network"):
            layer = "provider"

        properties = NodeProperties(
            cidr=", ".join(cidrs) if cidrs else None,
            gateway_ip=", ".join(gateway_ips) if gateway_ips else None,
            provider_network_type=network.get("provider:network_type"),
            provider_physical_network=network.get("provider:physical_network"),
            provider_segmentation_id=network.get("provider:segmentation_id"),
            is_external=is_external,
            is_shared=network.get("shared", False),
        )

        return TopologyNode(
            id=f"network:{network['id']}",
            resource_id=network["id"],
            resource_type="network",
            role="network",
            name=network["name"] or network["id"],
            project_id=network.get("project_id"),
            project_name=self.get_project_name(network.get("project_id")),
            status=network.get("status", "UNKNOWN"),
            layer=layer,
            properties=properties,
            tags=network.get("tags", []),
        )

    def normalize_subnet(self, subnet: dict) -> TopologyNode:
        """Normalize a Neutron subnet to a topology node."""
        properties = NodeProperties(
            cidr=subnet.get("cidr"),
            gateway_ip=subnet.get("gateway_ip"),
        )

        return TopologyNode(
            id=f"subnet:{subnet['id']}",
            resource_id=subnet["id"],
            resource_type="subnet",
            role="subnet",
            name=subnet["name"] or subnet.get("cidr", subnet["id"]),
            project_id=subnet.get("project_id"),
            project_name=self.get_project_name(subnet.get("project_id")),
            status="UNKNOWN",
            layer="network",
            properties=properties,
            tags=subnet.get("tags", []),
        )

    def normalize_router(self, router: dict) -> TopologyNode:
        """Normalize a Neutron router to a topology node."""
        external_gateway = None
        if router.get("external_gateway_info"):
            ext_gw = router["external_gateway_info"]
            external_gateway = {
                "network_id": ext_gw.get("network_id"),
                "enable_snat": ext_gw.get("enable_snat"),
            }

        properties = NodeProperties(
            is_external=bool(router.get("external_gateway_info")),
            external_gateway=external_gateway,
        )

        # Determine layer
        layer = "gateway"
        if router.get("external_gateway_info"):
            layer = "external"

        return TopologyNode(
            id=f"router:{router['id']}",
            resource_id=router["id"],
            resource_type="router",
            role="router",
            name=router["name"] or router["id"],
            project_id=router.get("project_id"),
            project_name=self.get_project_name(router.get("project_id")),
            status=router.get("status", "UNKNOWN"),
            layer=layer,
            properties=properties,
        )

    def normalize_ha_group(
        self,
        group_id: str,
        name: str,
        member_ids: list[str],
        vendor: str = None,
    ) -> TopologyNode:
        """Normalize a firewall HA group."""
        properties = NodeProperties(
            ha_members=member_ids,
        )

        return TopologyNode(
            id=f"ha-group:{group_id}",
            resource_id=group_id,
            resource_type="ha_group",
            role="firewall",
            name=name,
            project_id=None,
            project_name=None,
            status="ACTIVE",
            layer="gateway",
            properties=properties,
        )

    def create_internet_node(self) -> TopologyNode:
        """Create the synthetic Internet node."""
        return TopologyNode(
            id="internet",
            resource_id="internet",
            resource_type="internet",
            role="internet",
            name="Internet",
            project_id=None,
            project_name=None,
            status="ACTIVE",
            layer="internet",
            properties=NodeProperties(),
        )

    def normalize_trunk(
        self,
        trunk: dict,
        sub_ports: list[dict] = None,
    ) -> TopologyNode:
        """Normalize a Neutron trunk."""
        properties = NodeProperties()

        return TopologyNode(
            id=f"trunk:{trunk['id']}",
            resource_id=trunk["id"],
            resource_type="trunk",
            role="trunk",
            name=trunk["name"] or trunk["id"],
            project_id=trunk.get("project_id"),
            project_name=self.get_project_name(trunk.get("project_id")),
            status=trunk.get("status", "UNKNOWN"),
            layer="gateway",
            properties=properties,
        )
