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

    @staticmethod
    def _router_interfaces(
        router: dict,
        ports: dict,
        networks: dict,
        subnets: dict,
    ) -> list[dict]:
        """Resolve each router interface IP from its actual Neutron port."""
        interfaces = router.get("interfaces", [])
        if not interfaces:
            interfaces = [
                port for port in ports.values()
                if port.get("device_id") == router["id"]
                and port.get("device_owner_category") == "router_interface"
            ]

        resolved = []
        for interface in interfaces:
            port_id = interface.get("port_id") or interface.get("id")
            port = ports.get(port_id, {})
            network_id = interface.get("network_id") or port.get("network_id")
            fixed_ips = interface.get("fixed_ips") or port.get("fixed_ips") or []
            base = {
                "port_id": port_id,
                "network_id": network_id,
                "network_name": networks.get(network_id, {}).get("name"),
            }
            if not fixed_ips:
                resolved.append({**base, "subnet_id": None, "subnet_name": None,
                                 "subnet_cidr": None, "ip_address": None})
                continue
            for fixed_ip in fixed_ips:
                subnet_id = fixed_ip.get("subnet_id")
                subnet = subnets.get(subnet_id, {})
                resolved.append({
                    **base,
                    "subnet_id": subnet_id,
                    "subnet_name": subnet.get("name"),
                    "subnet_cidr": subnet.get("cidr"),
                    "ip_address": fixed_ip.get("ip_address"),
                })
        return resolved

    @staticmethod
    def _router_external_gateway(
        router: dict,
        ports: dict,
        networks: dict,
        subnets: dict,
    ) -> Optional[dict]:
        """Resolve external gateway metadata, falling back to gateway ports."""
        gateway_info = router.get("external_gateway_info")
        if not gateway_info:
            return None
        network_id = gateway_info.get("network_id")
        network = networks.get(network_id)
        if not network:
            return None

        fixed_ips = gateway_info.get("external_fixed_ips") or []
        if not any(item.get("ip_address") for item in fixed_ips):
            fixed_ips = [
                fixed_ip
                for port in ports.values()
                if port.get("device_id") == router["id"]
                and port.get("device_owner_category") == "router_gateway"
                and port.get("network_id") == network_id
                for fixed_ip in port.get("fixed_ips", [])
            ]

        normalized_ips = []
        for fixed_ip in fixed_ips:
            if not fixed_ip.get("ip_address"):
                continue
            subnet_id = fixed_ip.get("subnet_id")
            subnet = subnets.get(subnet_id, {})
            normalized_ips.append({
                "subnet_id": subnet_id,
                "subnet_name": subnet.get("name"),
                "subnet_cidr": subnet.get("cidr"),
                "ip_address": fixed_ip.get("ip_address"),
            })

        primary = normalized_ips[0] if normalized_ips else {}
        return {
            "network_id": network_id,
            "network_name": network.get("name"),
            "enable_snat": gateway_info.get("enable_snat"),
            "subnet_id": primary.get("subnet_id"),
            "subnet_name": primary.get("subnet_name"),
            "subnet_cidr": primary.get("subnet_cidr"),
            "ip_address": primary.get("ip_address"),
            "fixed_ips": normalized_ips,
        }

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
            router_interfaces = self._router_interfaces(
                router, ports, networks, subnets
            )
            external_gateway = self._router_external_gateway(
                router, ports, networks, subnets
            )
            router_node = self.normalizer.normalize_router({
                **router,
                "normalized_external_gateway": external_gateway,
            })
            router_node.properties.router_interfaces = router_interfaces
            self.add_node(router_node)

            # Router interface relationships
            for iface in router_interfaces:
                self.relationship_engine.add_router_interface_relationship(
                    router["id"],
                    iface["network_id"],
                    iface.get("port_id"),
                    properties={
                        "network_id": iface.get("network_id"),
                        "subnet_id": iface.get("subnet_id"),
                        "gateway_ip": iface.get("ip_address"),
                    },
                )

            # Preserve the infrastructure edge and add a direct visual
            # abstraction to Internet with enough metadata to explain it.
            if external_gateway:
                ext_net_id = external_gateway["network_id"]
                gateway_properties = {
                    "ip_address": external_gateway.get("ip_address"),
                    "external_network_id": ext_net_id,
                    "external_network_name": external_gateway.get("network_name"),
                    "external_subnet_id": external_gateway.get("subnet_id"),
                    "external_subnet_cidr": external_gateway.get("subnet_cidr"),
                    "connection_kind": "router_external_gateway",
                }
                self.relationship_engine.add_external_gateway_relationship(
                    router["id"],
                    ext_net_id,
                    properties=gateway_properties,
                )
                self.relationship_engine.add_device_internet_relationship(
                    "router",
                    router["id"],
                    ext_net_id,
                    gateway_properties,
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
                interface["is_external"] = bool(network.get("router:external"))
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

                    network = networks.get(port.get("network_id"), {})
                    if network.get("router:external"):
                        wan_ip = next(
                            (
                                fixed_ip.get("ip_address")
                                for fixed_ip in port.get("fixed_ips", [])
                                if fixed_ip.get("ip_address")
                            ),
                            None,
                        )
                        subnet_id = next(
                            (
                                fixed_ip.get("subnet_id")
                                for fixed_ip in port.get("fixed_ips", [])
                                if fixed_ip.get("ip_address")
                            ),
                            None,
                        )
                        self.relationship_engine.add_device_internet_relationship(
                            "server",
                            server["id"],
                            port["id"],
                            {
                                "port_id": port["id"],
                                "network_id": port.get("network_id"),
                                "ip_address": wan_ip,
                                "external_network_id": port.get("network_id"),
                                "external_network_name": network.get("name"),
                                "external_subnet_id": subnet_id,
                                "external_subnet_cidr": subnets.get(subnet_id, {}).get("cidr"),
                                "connection_kind": "vm_external_interface",
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
