"""Logical Internet path discovery over normalized, directed topology edges."""

from collections import deque

from app.schemas.topology import InternetPathResponse, TopologyEdge, TopologyNode


class PathEngine:
    """Find a declared or inferred directed path from a VM to Internet."""

    def __init__(self):
        self._nodes: dict[str, TopologyNode] = {}
        self._edges: list[TopologyEdge] = []

    def set_topology(
        self,
        nodes: list[TopologyNode],
        edges: list[TopologyEdge],
    ) -> None:
        """Replace the immutable snapshot searched by this engine."""
        self._nodes = {node.id: node for node in nodes}
        self._edges = list(edges)

    def find_internet_path(self, server_id: str) -> InternetPathResponse:
        """Find a path using only relationships present in the topology graph."""
        source = f"server:{server_id}"
        if source not in self._nodes:
            return self._not_found(
                source,
                f"Server {server_id} not found in topology",
                [],
            )

        adjacency: dict[str, list[tuple[str, TopologyEdge]]] = {}
        for edge in self._edges:
            # Ignore dangling targets. Internet is the one supported synthetic ID.
            if edge.target != "internet" and edge.target not in self._nodes:
                continue
            adjacency.setdefault(edge.source, []).append((edge.target, edge))

        queue = deque([(source, [source], 1.0, False)])
        visited = {source}
        deepest_path = [source]
        max_hops = 20

        while queue:
            current, path, confidence, inferred = queue.popleft()
            if len(path) - 1 >= max_hops:
                continue

            candidates = adjacency.get(current, [])
            candidates = sorted(candidates, key=lambda item: self._priority(item[0]))

            for target, edge in candidates:
                if target in visited:
                    continue

                next_path = [*path, target]
                next_inferred = inferred or edge.inferred
                next_confidence = confidence * edge.confidence if edge.inferred else confidence

                if len(next_path) > len(deepest_path):
                    deepest_path = next_path

                if target == "internet":
                    return InternetPathResponse(
                        source=source,
                        destination="internet",
                        found=True,
                        confidence=next_confidence,
                        path=next_path,
                        inferred=next_inferred,
                        path_nodes=self._get_path_nodes(next_path),
                    )

                visited.add(target)
                queue.append((target, next_path, next_confidence, next_inferred))

        return self._not_found(
            source,
            "No known egress gateway for this network",
            deepest_path,
        )

    def _priority(self, node_id: str) -> int:
        """Prefer gateway/external branches while retaining complete BFS coverage."""
        if node_id == "internet":
            return 0
        node = self._nodes.get(node_id)
        if not node:
            return 99
        if node.role == "firewall" or node.resource_type == "ha_group":
            return 1
        if node.role == "router":
            return 2
        if node.layer == "external":
            return 3
        if node.resource_type == "network":
            return 4
        return 10

    def _not_found(
        self,
        source: str,
        reason: str,
        path: list[str],
    ) -> InternetPathResponse:
        return InternetPathResponse(
            source=source,
            destination="internet",
            found=False,
            reason=reason,
            confidence=self.get_path_confidence(path) if path else 0.0,
            path=path,
            inferred=self._path_is_inferred(path),
            path_nodes=self._get_path_nodes(path),
        )

    def _find_edge(self, source: str, target: str) -> TopologyEdge | None:
        """Find a directed edge; direction represents logical traffic flow."""
        return next(
            (
                edge
                for edge in self._edges
                if edge.source == source and edge.target == target
            ),
            None,
        )

    def _path_is_inferred(self, path: list[str]) -> bool:
        return any(
            edge is not None and edge.inferred
            for edge in (
                self._find_edge(path[index], path[index + 1])
                for index in range(len(path) - 1)
            )
        )

    def _get_path_nodes(self, path: list[str]) -> list[TopologyNode]:
        return [self._nodes[node_id] for node_id in path if node_id in self._nodes]

    def get_path_confidence(self, path: list[str]) -> float:
        """Multiply confidence only for inferred edges in a known path."""
        if len(path) < 2:
            return 1.0

        confidence = 1.0
        for index in range(len(path) - 1):
            edge = self._find_edge(path[index], path[index + 1])
            if edge is None:
                return 0.0
            if edge.inferred:
                confidence *= edge.confidence
        return confidence
