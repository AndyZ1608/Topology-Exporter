"""
Topology relationship engine - builds edges between topology nodes.
"""
import logging
from typing import Optional
from app.schemas.topology import TopologyEdge, EdgeProperties

logger = logging.getLogger(__name__)


class RelationshipEngine:
    """Builds relationships between topology nodes."""

    def __init__(self):
        self._edges: list[TopologyEdge] = []
        self._port_to_server: dict[str, str] = {}
        self._port_to_network: dict[str, str] = {}
        self._server_to_ports: dict[str, list[str]] = {}
        self._network_to_subnets: dict[str, list[str]] = {}

    def reset(self):
        """Reset all tracked relationships."""
        self._edges = []
        self._port_to_server = {}
        self._port_to_network = {}
        self._server_to_ports = {}
        self._network_to_subnets = {}

    def add_edge(self, edge: TopologyEdge) -> TopologyEdge:
        """Add an already-normalized edge without exposing internal storage."""
        self._edges.append(edge)
        return edge

    def add_server_port_relationship(
        self,
        server_id: str,
        port_id: str,
        network_id: str,
        properties: dict = None,
    ) -> TopologyEdge:
        """Add a server-to-network attachment relationship."""
        edge_id = f"edge-{server_id}-{port_id}"

        # Track mappings
        self._port_to_server[port_id] = server_id
        self._port_to_network[port_id] = network_id
        if server_id not in self._server_to_ports:
            self._server_to_ports[server_id] = []
        self._server_to_ports[server_id].append(port_id)

        edge = TopologyEdge(
            id=edge_id,
            source=f"server:{server_id}",
            target=f"network:{network_id}",
            relationship="attached_to",
            inferred=False,
            confidence=1.0,
            properties=EdgeProperties(
                port_id=port_id,
                **(properties or {}),
            ),
        )
        self._edges.append(edge)
        return edge

    def add_subnet_relationship(
        self,
        network_id: str,
        subnet_id: str,
    ) -> TopologyEdge:
        """Add a network-to-subnet containment relationship."""
        edge_id = f"edge-{network_id}-{subnet_id}"

        if network_id not in self._network_to_subnets:
            self._network_to_subnets[network_id] = []
        self._network_to_subnets[network_id].append(subnet_id)

        edge = TopologyEdge(
            id=edge_id,
            source=f"network:{network_id}",
            target=f"subnet:{subnet_id}",
            relationship="contains",
            inferred=False,
            confidence=1.0,
        )
        self._edges.append(edge)
        return edge

    def add_router_interface_relationship(
        self,
        router_id: str,
        network_id: str,
        port_id: str = None,
        properties: dict = None,
    ) -> TopologyEdge:
        """Add a router-to-network interface relationship."""
        discriminator = port_id or network_id
        subnet_id = (properties or {}).get("subnet_id")
        if subnet_id:
            discriminator = f"{discriminator}-{subnet_id}"
        edge_id = f"edge-router-{router_id}-{discriminator}"

        edge = TopologyEdge(
            id=edge_id,
            source=f"network:{network_id}",
            target=f"router:{router_id}",
            relationship="router_interface",
            inferred=False,
            confidence=1.0,
            properties=EdgeProperties(port_id=port_id, **(properties or {})),
        )
        self._edges.append(edge)
        return edge

    def add_external_gateway_relationship(
        self,
        router_id: str,
        external_network_id: str,
        properties: dict = None,
    ) -> TopologyEdge:
        """Add a router-to-external-network gateway relationship."""
        edge_id = f"edge-external-{router_id}-{external_network_id}"

        edge = TopologyEdge(
            id=edge_id,
            source=f"router:{router_id}",
            target=f"network:{external_network_id}",
            relationship="external_gateway",
            inferred=False,
            confidence=1.0,
            properties=EdgeProperties(**(properties or {})),
        )
        self._edges.append(edge)
        return edge

    def add_internet_relationship(
        self,
        external_network_id: str,
        confidence: float = 0.9,
    ) -> TopologyEdge:
        """Add an external-network-to-Internet relationship."""
        edge_id = f"edge-internet-{external_network_id}"

        edge = TopologyEdge(
            id=edge_id,
            source=f"network:{external_network_id}",
            target="internet",
            relationship="internet_uplink",
            inferred=True,
            confidence=confidence,
        )
        self._edges.append(edge)
        return edge

    def add_device_internet_relationship(
        self,
        resource_type: str,
        resource_id: str,
        discriminator: str,
        properties: dict,
    ) -> TopologyEdge:
        """Add a visible device-to-Internet abstraction backed by real data."""
        edge = TopologyEdge(
            id=f"edge-internet-{resource_type}-{resource_id}-{discriminator}",
            source=f"{resource_type}:{resource_id}",
            target="internet",
            relationship="internet_uplink",
            inferred=False,
            confidence=1.0,
            properties=EdgeProperties(**properties),
        )
        self._edges.append(edge)
        return edge

    def get_edges(self) -> list[TopologyEdge]:
        """Get all edges."""
        return self._edges

    def get_server_network(self, server_id: str) -> Optional[str]:
        """Get the network a server is attached to (first port)."""
        ports = self._server_to_ports.get(server_id, [])
        if ports:
            port_id = ports[0]
            return self._port_to_network.get(port_id)
        return None

    def get_network_servers(self, network_id: str) -> list[str]:
        """Get all servers attached to a network."""
        servers = []
        for port_id, net_id in self._port_to_network.items():
            if net_id == network_id:
                server_id = self._port_to_server.get(port_id)
                if server_id:
                    servers.append(server_id)
        return servers

    def get_upstream_nodes(self, node_id: str) -> list[str]:
        """Get nodes upstream from a given node."""
        upstream = []
        for edge in self._edges:
            if edge.target == node_id:
                upstream.append(edge.source)
        return upstream

    def get_downstream_nodes(self, node_id: str) -> list[str]:
        """Get nodes downstream from a given node."""
        downstream = []
        for edge in self._edges:
            if edge.source == node_id:
                downstream.append(edge.target)
        return downstream
