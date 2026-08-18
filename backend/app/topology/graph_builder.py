"""
Graph builder - orchestrates topology building from OpenStack resources.
"""
import logging
from typing import Optional

from app.schemas.topology import TopologyNode, TopologyEdge, TopologyResponse
from app.topology.normalizer import TopologyNormalizer
from app.topology.classifier import ClassificationEngine
from app.topology.relationship_engine import RelationshipEngine
from app.topology.path_engine import PathEngine

logger = logging.getLogger(__name__)


class GraphBuilder:
    """
    Main topology graph builder.

    Orchestrates collection, normalization, classification,
    relationship building, and graph generation.
    """

    def __init__(self):
        self.normalizer = TopologyNormalizer()
        self.classifier = ClassificationEngine()
        self.relationship_engine = RelationshipEngine()
        self.path_engine = PathEngine()

        self._nodes: list[TopologyNode] = []
        self._edges: list[TopologyEdge] = []
        self._nodes_by_id: dict[str, TopologyNode] = {}
        self._nodes_by_resource: dict[str, TopologyNode] = {}

    def reset(self):
        """Reset the graph state."""
        self._nodes = []
        self._edges = []
        self._nodes_by_id = {}
        self._nodes_by_resource = {}
        self.relationship_engine.reset()

    def add_node(self, node: TopologyNode):
        """Add a node to the graph."""
        self._nodes.append(node)
        self._nodes_by_id[node.id] = node
        if node.resource_type != "internet":
            self._nodes_by_resource[f"{node.resource_type}:{node.resource_id}"] = node

    def add_edge(self, edge: TopologyEdge):
        """Add an edge to the graph."""
        self._edges.append(edge)

    def get_node(self, node_id: str) -> Optional[TopologyNode]:
        """Get a node by ID."""
        return self._nodes_by_id.get(node_id)

    def get_node_by_resource(self, resource_type: str, resource_id: str) -> Optional[TopologyNode]:
        """Get a node by resource type and ID."""
        return self._nodes_by_resource.get(f"{resource_type}:{resource_id}")

    def build_from_openstack(
        self,
        projects: dict,
        servers: dict,
        networks: dict,
        subnets: dict,
        ports: dict,
        routers: dict,
        floating_ips: dict,
        trunks: dict,
        security_groups: dict,
    ) -> TopologyResponse:
        """
        Build topology graph from OpenStack resources.

        This is the main entry point for topology generation.
        """
        self.reset()

        # Set project names for normalization
        project_names = {pid: pdata["name"] for pid, pdata in projects.items()}
        self.normalizer.set_project_names(project_names)

        # Group ports by server and network
        ports_by_server: dict[str, list[dict]] = {}

        for port in ports.values():
            server_id = port.get("device_id")
            if server_id and port.get("device_owner_category") == "compute":
                if server_id not in ports_by_server:
                    ports_by_server[server_id] = []
                ports_by_server[server_id].append(port)

        # A trunk subport may not carry the Nova device_id. Attribute it to the
        # parent port's server so one VM keeps all of its real network links.
        for trunk in trunks.values():
            parent_port = ports.get(trunk.get("port_id"))
            server_id = parent_port.get("device_id") if parent_port else None
            if not server_id or parent_port.get("device_owner_category") != "compute":
                continue
            known_port_ids = {port["id"] for port in ports_by_server.get(server_id, [])}
            for sub_port in trunk.get("sub_ports", []):
                port = ports.get(sub_port.get("port_id"))
                if port and port["id"] not in known_port_ids:
                    ports_by_server.setdefault(server_id, []).append({
                        **port,
                        "_trunk_parent_server_id": server_id,
                    })
                    known_port_ids.add(port["id"])

        # 1. Add networks. Subnet CIDRs/gateways are folded into the network
        # node for the operational graph instead of becoming large visual nodes.
        for network in networks.values():
            network_subnets = [
                s for s in subnets.values()
                if s["network_id"] == network["id"]
            ]
            network_node = self.normalizer.normalize_network(network, network_subnets)
            network_node.properties.vm_count = len({
                server_id
                for server_id, server_ports in ports_by_server.items()
                if any(port.get("network_id") == network["id"] for port in server_ports)
            })
            network_node.properties.subnets = [
                {
                    "id": subnet["id"],
                    "name": subnet.get("name"),
                    "cidr": subnet.get("cidr"),
                    "gateway_ip": subnet.get("gateway_ip"),
                }
                for subnet in network_subnets
            ]
            self.add_node(network_node)

        # 2. Add routers
        for router in routers.values():
            router_node = self.normalizer.normalize_router(router)
            router_node.properties.router_interfaces = [
                {
                    "port_id": interface.get("port_id"),
                    "network_id": interface.get("network_id"),
                    "network_name": networks.get(interface.get("network_id"), {}).get("name"),
                    "subnets": [
                        subnet.get("cidr")
                        for subnet in subnets.values()
                        if subnet.get("network_id") == interface.get("network_id")
                        and subnet.get("cidr")
                    ],
                }
                for interface in router.get("interfaces", [])
            ]
            self.add_node(router_node)

            # Router interface relationships
            for iface in router.get("interfaces", []):
                self.relationship_engine.add_router_interface_relationship(
                    router["id"],
                    iface["network_id"],
                    iface.get("port_id"),
                )

            # External gateway relationship
            if router.get("external_gateway_info"):
                ext_net_id = router["external_gateway_info"]["network_id"]
                self.relationship_engine.add_external_gateway_relationship(
                    router["id"],
                    ext_net_id,
                )

        # 3. Add servers (VMs and firewalls)
        for server in servers.values():
            server_ports = ports_by_server.get(server["id"], [])

            # Get floating IPs for this server
            server_fips = [
                fip["floating_ip_address"]
                for fip in floating_ips.values()
                if fip.get("port_id") in [p["id"] for p in server_ports]
            ]

            # Classify the server
            classification = self.classifier.classify_server(
                server,
                server_ports,
                networks,
            )
            # Create node
            server_node = self.normalizer.normalize_server(
                server,
                server_ports,
                server_fips,
            )

            # Update role based on classification
            server_node.role = classification["role"]
            for port_id, interface_classification in classification["interfaces"].items():
                server_node.properties.interfaces.setdefault(port_id, {}).update(
                    interface_classification
                )
            for interface in server_node.properties.interfaces.values():
                network = networks.get(interface.get("network_id"), {})
                interface["network_name"] = network.get("name")
                interface["subnets"] = [
                    {
                        "id": subnet_id,
                        "name": subnets.get(subnet_id, {}).get("name"),
                        "cidr": subnets.get(subnet_id, {}).get("cidr"),
                    }
                    for subnet_id in interface.get("subnet_ids", [])
                ]
            server_node.properties.security_groups = sorted({
                security_groups.get(group_id, {}).get("name", group_id)
                for port in server_ports
                for group_id in port.get("security_groups", [])
            })
            server_node.properties.metadata["vendor"] = classification["vendor"]

            self.add_node(server_node)

            # Create port relationships
            for port in server_ports:
                if (
                    port.get("device_owner_category") == "compute"
                    or port.get("_trunk_parent_server_id") == server["id"]
                ):
                    self.relationship_engine.add_server_port_relationship(
                        server["id"],
                        port["id"],
                        port["network_id"],
                        properties={
                            "fixed_ip": next(
                                (
                                    fixed_ip.get("ip_address")
                                    for fixed_ip in port.get("fixed_ips", [])
                                    if fixed_ip.get("ip_address")
                                ),
                                None,
                            ),
                            "subnet_id": next(
                                (
                                    fixed_ip.get("subnet_id")
                                    for fixed_ip in port.get("fixed_ips", [])
                                    if fixed_ip.get("subnet_id")
                                ),
                                None,
                            ),
                            "network_id": port["network_id"],
                            "mac_address": port.get("mac_address"),
                        },
                    )

                    # Floating IPs are exposed on the server's properties. They
                    # are not graph nodes by default, so do not create dangling
                    # edges to non-existent floating-IP nodes.

        # 4. Add the conceptual Internet endpoint and only OpenStack external
        # network uplinks. No external physical infrastructure is injected.
        internet_node = self.normalizer.create_internet_node()
        self.add_node(internet_node)

        # Connect external/provider networks to Internet
        for network in networks.values():
            if network.get("router:external") or network.get("provider:physical_network"):
                # Check if it's a significant external network
                if self._is_internet_egress_network(network):
                    self.relationship_engine.add_internet_relationship(network["id"])

        # 5. Collect all edges
        for edge in self.relationship_engine.get_edges():
            self.add_edge(edge)

        # 6. Update path engine
        self.path_engine.set_topology(self._nodes, self._edges)

        return TopologyResponse(
            nodes=self._nodes,
            edges=self._edges,
            metadata={
                "total_nodes": len(self._nodes),
                "total_edges": len(self._edges),
                "servers": len(servers),
                "networks": len(networks),
                "routers": len(routers),
                "subnets": len(subnets),
                "floating_ips": len(floating_ips),
            },
        )

    def _is_internet_egress_network(self, network: dict) -> bool:
        """Determine if a network represents Internet egress."""
        # External networks with router:external=True
        if network.get("router:external"):
            return True

        # Explicit operator tags can mark non-Neutron-external provider networks.
        tags = network.get("tags", [])
        for tag in tags:
            if tag.lower() in ["wan", "internet", "internet_egress", "public"]:
                return True

        return False


    def find_internet_path(self, server_id: str) -> dict:
        """Find the Internet path for a server."""
        return self.path_engine.find_internet_path(server_id).model_dump()
