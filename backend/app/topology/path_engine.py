"""
Internet path engine - finds the logical path from a VM to the Internet.
"""
import logging
from typing import Optional

from app.schemas.topology import TopologyNode, InternetPathResponse

logger = logging.getLogger(__name__)


class PathEngine:
    """
    Finds the logical path from a VM to the Internet.

    This is an inference engine - it analyzes the topology to determine
    the likely traffic path, but does not verify packet-level routing.
    """

    def __init__(self):
        self._nodes: dict[str, TopologyNode] = {}
        self._edges: list = []
        self._node_by_resource: dict[str, str] = {}

    def set_topology(self, nodes: list[TopologyNode], edges: list):
        """Set the current topology."""
        self._nodes = {n.id: n for n in nodes}
        self._edges = edges

        # Build resource_id to node_id mapping
        self._node_by_resource = {}
        for node in nodes:
            if node.resource_type != "internet":
                self._node_by_resource[f"{node.resource_type}:{node.resource_id}"] = node.id

    def find_internet_path(
        self,
        server_id: str,
    ) -> InternetPathResponse:
        """
        Find the logical path from a server to the Internet.

        Algorithm:
        1. Start at the server node
        2. Follow network connections upstream
        3. Look for router/firewall/external network chain
        4. Determine if this leads to Internet

        Returns:
            InternetPathResponse with path information
        """
        server_node_id = f"server:{server_id}"

        if server_node_id not in self._nodes:
            return InternetPathResponse(
                source=server_node_id,
                destination="internet",
                found=False,
                reason=f"Server {server_id} not found in topology",
                confidence=0.0,
                path=[],
                inferred=False,
                path_nodes=[],
            )

        path = [server_node_id]
        current_node_id = server_node_id
        visited = {server_node_id}
        confidence = 1.0
        inferred_count = 0

        # Build adjacency maps
        downstream: dict[str, list[str]] = {}
        upstream: dict[str, list[str]] = {}

        for edge in self._edges:
            if edge.source not in downstream:
                downstream[edge.source] = []
            downstream[edge.source].append(edge.target)

            if edge.target not in upstream:
                upstream[edge.target] = []
            upstream[edge.target].append(edge.source)

        # Traverse upstream (from VM toward gateway)
        max_hops = 20  # Prevent infinite loops
        hops = 0

        while hops < max_hops:
            hops += 1

            # Get upstream nodes
            up_nodes = upstream.get(current_node_id, [])

            if not up_nodes:
                # End of path - couldn't reach Internet
                return InternetPathResponse(
                    source=server_node_id,
                    destination="internet",
                    found=False,
                    reason="No gateway found - this network may not have external connectivity",
                    confidence=confidence,
                    path=path,
                    inferred=inferred_count > 0,
                    path_nodes=self._get_path_nodes(path),
                )

            # Find the best next node
            # Priority: router > firewall > external network > other
            next_node = None
            next_node_type_priority = 999

            for candidate in up_nodes:
                if candidate in visited:
                    continue

                node = self._nodes.get(candidate)
                if not node:
                    continue

                # Determine priority
                priority = 999
                if node.role == "router":
                    priority = 1
                elif node.role == "firewall":
                    priority = 2
                elif node.layer == "external":
                    priority = 3
                elif node.resource_type == "network":
                    priority = 4
                elif node.role == "network":
                    priority = 4

                if priority < next_node_type_priority:
                    next_node = candidate
                    next_node_type_priority = priority

            if not next_node:
                # Dead end
                return InternetPathResponse(
                    source=server_node_id,
                    destination="internet",
                    found=False,
                    reason="No viable path to external network",
                    confidence=confidence,
                    path=path,
                    inferred=inferred_count > 0,
                    path_nodes=self._get_path_nodes(path),
                )

            # Move to next node
            path.append(next_node)
            visited.add(next_node)
            current_node_id = next_node

            # Check if we reached Internet
            if next_node == "internet":
                return InternetPathResponse(
                    source=server_node_id,
                    destination="internet",
                    found=True,
                    confidence=confidence,
                    path=path,
                    inferred=inferred_count > 0,
                    path_nodes=self._get_path_nodes(path),
                )

            # Check if we reached an external network
            node = self._nodes.get(next_node)
            if node and node.layer == "external":
                # Check if this external network connects to Internet
                if self._connects_to_internet(next_node):
                    path.append("internet")
                    return InternetPathResponse(
                        source=server_node_id,
                        destination="internet",
                        found=True,
                        confidence=confidence,
                        path=path,
                        inferred=True,
                        path_nodes=self._get_path_nodes(path),
                    )

            # Track inferred edges
            edge = self._find_edge(current_node_id, next_node)
            if edge and edge.inferred:
                inferred_count += 1
                confidence *= edge.confidence

        # Max hops exceeded
        return InternetPathResponse(
            source=server_node_id,
            destination="internet",
            found=False,
            reason="Maximum path length exceeded",
            confidence=confidence,
            path=path,
            inferred=True,
            path_nodes=self._get_path_nodes(path),
        )

    def _connects_to_internet(self, network_id: str) -> bool:
        """Check if a network connects directly to Internet."""
        for edge in self._edges:
            if edge.source == network_id and edge.target == "internet":
                return True
            if edge.target == network_id and edge.relationship == "internet_uplink":
                return True
        return False

    def _find_edge(self, source: str, target: str):
        """Find edge between two nodes."""
        for edge in self._edges:
            if edge.source == source and edge.target == target:
                return edge
            if edge.source == target and edge.target == source:
                return edge
        return None

    def _get_path_nodes(self, path: list[str]) -> list[TopologyNode]:
        """Get node objects for a path."""
        nodes = []
        for node_id in path:
            if node_id == "internet":
                # Create synthetic Internet node
                nodes.append(TopologyNode(
                    id="internet",
                    resource_id="internet",
                    resource_type="internet",
                    role="internet",
                    name="Internet",
                    layer="internet",
                    status="ACTIVE",
                ))
            elif node_id in self._nodes:
                nodes.append(self._nodes[node_id])
        return nodes

    def get_path_confidence(self, path: list[str]) -> float:
        """Calculate confidence score for a path based on inferred edges."""
        if len(path) < 2:
            return 1.0

        confidence = 1.0
        for i in range(len(path) - 1):
            edge = self._find_edge(path[i], path[i + 1])
            if edge:
                if edge.inferred:
                    confidence *= edge.confidence
            else:
                # No edge found - very low confidence
                confidence *= 0.5

        return confidence
