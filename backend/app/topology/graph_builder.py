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
        ports_by_network: dict[str, list[dict]] = {}

        for port in ports.values():
            server_id = port.get("device_id")
            network_id = port.get("network_id")

            if server_id and port.get("device_owner_category") == "compute":
                if server_id not in ports_by_server:
                    ports_by_server[server_id] = []
                ports_by_server[server_id].append(port)

            if network_id:
                if network_id not in ports_by_network:
                    ports_by_network[network_id] = []
                ports_by_network[network_id].append(port)

        # 1. Add networks and subnets first
        for network in networks.values():
            network_subnets = [
                s for s in subnets.values()
                if s["network_id"] == network["id"]
            ]
            network_node = self.normalizer.normalize_network(network, network_subnets)
            self.add_node(network_node)

            # Add subnet nodes
            for subnet in network_subnets:
                subnet_node = self.normalizer.normalize_subnet(subnet)
                self.add_node(subnet_node)
                self.relationship_engine.add_subnet_relationship(network["id"], subnet["id"])

        # 2. Add routers
        for router in routers.values():
            router_node = self.normalizer.normalize_router(router)
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
        server_classifications = {}

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
            server_classifications[server["id"]] = classification

            # Create node
            server_node = self.normalizer.normalize_server(
                server,
                server_ports,
                server_fips,
            )

            # Update role based on classification
            server_node.role = classification["role"]
            server_node.properties.interfaces = classification["interfaces"]
            server_node.properties.metadata["vendor"] = classification["vendor"]
            server_node.properties.metadata["ha_group"] = classification["ha_group"]

            self.add_node(server_node)

            # Create port relationships
            for port in server_ports:
                if port.get("device_owner_category") == "compute":
                    self.relationship_engine.add_server_port_relationship(
                        server["id"],
                        port["id"],
                        port["network_id"],
                    )

                    # Add floating IP relationships
                    for fip in floating_ips.values():
                        if fip.get("port_id") == port["id"]:
                            self.relationship_engine.add_floating_ip_relationship(
                                server["id"],
                                fip["floating_ip_address"],
                                fip.get("fixed_ip_address"),
                                port["id"],
                            )

        # 4. Handle HA groups
        ha_groups = self.classifier.get_ha_groups(list(servers.values()), ports)

        for ha_group_id, member_ids in ha_groups.items():
            if len(member_ids) >= 2:
                # Create HA group node
                vendor = "Unknown"
                for member_id in member_ids:
                    if member_id in server_classifications:
                        v = server_classifications[member_id].get("vendor")
                        if v:
                            vendor = v
                            break

                ha_group_node = self.normalizer.normalize_ha_group(
                    ha_group_id,
                    f"{vendor} HA",
                    member_ids,
                    vendor,
                )
                self.add_node(ha_group_node)

                # Add member relationships
                for member_id in member_ids:
                    self.relationship_engine.add_ha_group_relationship(ha_group_id, member_id)

        # 5. Handle trunks
        for trunk in trunks.values():
            trunk_node = self.normalizer.normalize_trunk(trunk)
            self.add_node(trunk_node)

            # Find the parent port (firewall)
            parent_port_id = trunk.get("port_id")
            if parent_port_id and parent_port_id in ports:
                port = ports[parent_port_id]
                device_id = port.get("device_id")
                if device_id and device_id in server_classifications:
                    if server_classifications[device_id]["role"] == "firewall":
                        self.relationship_engine.add_trunk_parent_relationship(
                            trunk["id"],
                            parent_port_id,
                            device_id,
                        )

            # Add subport relationships
            for sub_port in trunk.get("sub_ports", []):
                sub_port_id = sub_port.get("port_id")
                if sub_port_id and sub_port_id in ports:
                    sub_port_network_id = ports[sub_port_id].get("network_id")
                    if sub_port_network_id:
                        self.relationship_engine.add_trunk_subport_relationship(
                            trunk["id"],
                            sub_port,
                            sub_port_network_id,
                        )

        # 6. Add Internet node and relationships
        internet_node = self.normalizer.create_internet_node()
        self.add_node(internet_node)

        # Connect external/provider networks to Internet
        for network in networks.values():
            if network.get("router:external") or network.get("provider:physical_network"):
                # Check if it's a significant external network
                if self._is_internet_egress_network(network):
                    self.relationship_engine.add_internet_relationship(network["id"])

        # 7. Build inferred firewall relationships
        self._build_inferred_firewall_paths(servers, ports, server_classifications, networks)

        # 8. Collect all edges
        for edge in self.relationship_engine.get_edges():
            self.add_edge(edge)

        # 9. Update path engine
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
                "ha_groups": len([n for n in self._nodes if n.resource_type == "ha_group"]),
            },
        )

    def _is_internet_egress_network(self, network: dict) -> bool:
        """Determine if a network represents Internet egress."""
        # External networks with router:external=True
        if network.get("router:external"):
            return True

        # Provider networks
        if network.get("provider:physical_network"):
            name = network.get("name", "").lower()
            if any(keyword in name for keyword in ["wan", "internet", "ext", "external", "public"]):
                return True

        # Check tags
        tags = network.get("tags", [])
        for tag in tags:
            if tag.lower() in ["wan", "internet", "internet_egress", "public"]:
                return True

        return False

    def _build_inferred_firewall_paths(
        self,
        servers: dict,
        ports: dict,
        classifications: dict,
        networks: dict,
    ):
        """
        Build inferred paths showing VMs that egress through firewalls.

        This is a heuristic-based inference, not verified routing.
        """
        # Find firewalls
        firewalls = {
            server_id: classification
            for server_id, classification in classifications.items()
            if classification["role"] == "firewall"
        }

        # Find networks connected to firewalls
        firewall_networks: dict[str, str] = {}  # network_id -> firewall_server_id

        for server_id, classification in firewalls.items():
            for port_id, iface_info in classification.get("interfaces", {}).items():
                if iface_info.get("role") in ["WAN", "TRUNK"]:
                    network_id = iface_info.get("network_id")
                    if network_id:
                        firewall_networks[network_id] = server_id

        # For each VM, check if there's an inferred path through a firewall
        for server_id, server in servers.items():
            if server_id in firewalls:
                continue  # Skip firewalls

            classification = classifications.get(server_id, {})
            if classification.get("role") == "vm":
                server_ports = [
                    p for p in ports.values()
                    if p.get("device_id") == server_id and p.get("device_owner_category") == "compute"
                ]

                for port in server_ports:
                    network_id = port.get("network_id")
                    if network_id in firewall_networks:
                        firewall_id = firewall_networks[network_id]

                        # Check if firewall has a path to external/Internet
                        firewall_classification = firewalls.get(firewall_id, {})
                        if firewall_classification.get("interfaces"):
                            # This is an inferred relationship
                            self.relationship_engine.add_inferred_firewall_relationship(
                                server_id,
                                firewall_id,
                                network_id,
                                confidence=0.75,
                            )

    def find_internet_path(self, server_id: str) -> dict:
        """Find the Internet path for a server."""
        return self.path_engine.find_internet_path(server_id).model_dump()
