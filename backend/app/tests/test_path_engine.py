"""
Unit tests for the path engine.
"""
import pytest
from app.topology.path_engine import PathEngine
from app.schemas.topology import TopologyNode, TopologyEdge, NodeProperties


class TestPathEngine:
    """Tests for PathEngine."""

    @pytest.fixture
    def engine(self):
        return PathEngine()

    @pytest.fixture
    def sample_topology(self, engine):
        """Create a sample topology for testing."""
        nodes = [
            TopologyNode(
                id="server:vm-1",
                resource_id="vm-1",
                resource_type="server",
                role="vm",
                name="web-server",
                status="ACTIVE",
                layer="workload",
            ),
            TopologyNode(
                id="network:vlan100",
                resource_id="vlan100",
                resource_type="network",
                role="network",
                name="VLAN100",
                status="ACTIVE",
                layer="network",
            ),
            TopologyNode(
                id="server:fw-1",
                resource_id="fw-1",
                resource_type="server",
                role="firewall",
                name="PAN01",
                status="ACTIVE",
                layer="gateway",
            ),
            TopologyNode(
                id="network:wan",
                resource_id="wan",
                resource_type="network",
                role="network",
                name="NOC-WAN",
                status="ACTIVE",
                layer="external",
                properties=NodeProperties(is_external=True),
            ),
            TopologyNode(
                id="internet",
                resource_id="internet",
                resource_type="internet",
                role="internet",
                name="Internet",
                status="ACTIVE",
                layer="internet",
            ),
        ]

        edges = [
            TopologyEdge(
                id="edge-1",
                source="server:vm-1",
                target="network:vlan100",
                relationship="attached_to",
                inferred=False,
                confidence=1.0,
            ),
            TopologyEdge(
                id="edge-2",
                source="network:vlan100",
                target="server:fw-1",
                relationship="egress_via",
                inferred=True,
                confidence=0.8,
            ),
            TopologyEdge(
                id="edge-3",
                source="server:fw-1",
                target="network:wan",
                relationship="attached_to",
                inferred=False,
                confidence=1.0,
            ),
            TopologyEdge(
                id="edge-4",
                source="network:wan",
                target="internet",
                relationship="internet_uplink",
                inferred=True,
                confidence=0.95,
            ),
        ]

        engine.set_topology(nodes, edges)
        return nodes, edges

    def test_find_internet_path_success(self, engine, sample_topology):
        """Test finding internet path for a VM with firewall."""
        nodes, edges = sample_topology

        result = engine.find_internet_path("vm-1")

        assert result.found is True
        assert result.destination == "internet"
        assert "server:vm-1" in result.path
        assert "internet" in result.path
        assert len(result.path) > 0

    def test_find_internet_path_server_not_found(self, engine, sample_topology):
        """Test finding path for non-existent server."""
        result = engine.find_internet_path("nonexistent")

        assert result.found is False
        assert "not found" in result.reason.lower()

    def test_find_internet_path_no_gateway(self, engine):
        """Test path when VM has no gateway."""
        nodes = [
            TopologyNode(
                id="server:vm-isolated",
                resource_id="vm-isolated",
                resource_type="server",
                role="vm",
                name="isolated-vm",
                status="ACTIVE",
                layer="workload",
            ),
            TopologyNode(
                id="network:isolated",
                resource_id="isolated",
                resource_type="network",
                role="network",
                name="Isolated Network",
                status="ACTIVE",
                layer="network",
            ),
        ]

        edges = [
            TopologyEdge(
                id="edge-isolated",
                source="server:vm-isolated",
                target="network:isolated",
                relationship="attached_to",
                inferred=False,
                confidence=1.0,
            ),
        ]

        engine.set_topology(nodes, edges)
        result = engine.find_internet_path("vm-isolated")

        assert result.found is False
        assert result.reason is not None

    def test_path_with_only_confirmed_relationships(self, engine):
        """Test path with only confirmed relationships."""
        nodes = [
            TopologyNode(
                id="server:vm-direct",
                resource_id="vm-direct",
                resource_type="server",
                role="vm",
                name="direct-vm",
                status="ACTIVE",
                layer="workload",
            ),
            TopologyNode(
                id="network:ext",
                resource_id="ext",
                resource_type="network",
                role="network",
                name="External",
                status="ACTIVE",
                layer="external",
                properties=NodeProperties(is_external=True),
            ),
            TopologyNode(
                id="internet",
                resource_id="internet",
                resource_type="internet",
                role="internet",
                name="Internet",
                status="ACTIVE",
                layer="internet",
            ),
        ]

        edges = [
            TopologyEdge(
                id="edge-direct-1",
                source="server:vm-direct",
                target="network:ext",
                relationship="attached_to",
                inferred=False,
                confidence=1.0,
            ),
            TopologyEdge(
                id="edge-direct-2",
                source="network:ext",
                target="internet",
                relationship="internet_uplink",
                inferred=True,
                confidence=1.0,
            ),
        ]

        engine.set_topology(nodes, edges)
        result = engine.find_internet_path("vm-direct")

        assert result.found is True
        assert result.inferred is True  # Still has inferred due to internet link

    def test_get_path_confidence(self, engine, sample_topology):
        """Test path confidence calculation."""
        nodes, edges = sample_topology

        path = ["server:vm-1", "network:vlan100", "server:fw-1", "network:wan", "internet"]
        confidence = engine.get_path_confidence(path)

        # Should multiply inferred edges' confidence
        assert 0 < confidence <= 1.0

    def test_empty_topology(self, engine):
        """Test path finding on empty topology."""
        result = engine.find_internet_path("any-server")

        assert result.found is False
        assert "not found" in result.reason.lower()

    def test_path_with_router(self, engine):
        """Test path finding with Neutron router."""
        nodes = [
            TopologyNode(
                id="server:vm-router",
                resource_id="vm-router",
                resource_type="server",
                role="vm",
                name="router-test-vm",
                status="ACTIVE",
                layer="workload",
            ),
            TopologyNode(
                id="network:internal",
                resource_id="internal",
                resource_type="network",
                role="network",
                name="Internal",
                status="ACTIVE",
                layer="network",
            ),
            TopologyNode(
                id="router:router-1",
                resource_id="router-1",
                resource_type="router",
                role="router",
                name="test-router",
                status="ACTIVE",
                layer="gateway",
            ),
            TopologyNode(
                id="network:ext",
                resource_id="ext",
                resource_type="network",
                role="network",
                name="External",
                status="ACTIVE",
                layer="external",
                properties=NodeProperties(is_external=True),
            ),
            TopologyNode(
                id="internet",
                resource_id="internet",
                resource_type="internet",
                role="internet",
                name="Internet",
                status="ACTIVE",
                layer="internet",
            ),
        ]

        edges = [
            TopologyEdge(
                id="edge-vm-net",
                source="server:vm-router",
                target="network:internal",
                relationship="attached_to",
                inferred=False,
                confidence=1.0,
            ),
            TopologyEdge(
                id="edge-net-router",
                source="network:internal",
                target="router:router-1",
                relationship="router_interface",
                inferred=False,
                confidence=1.0,
            ),
            TopologyEdge(
                id="edge-router-ext",
                source="router:router-1",
                target="network:ext",
                relationship="external_gateway",
                inferred=False,
                confidence=1.0,
            ),
            TopologyEdge(
                id="edge-ext-inet",
                source="network:ext",
                target="internet",
                relationship="internet_uplink",
                inferred=True,
                confidence=0.9,
            ),
        ]

        engine.set_topology(nodes, edges)
        result = engine.find_internet_path("vm-router")

        assert result.found is True
        assert "internet" in result.path

    def test_long_path_max_hops(self, engine):
        """Test that max hops prevents infinite loops."""
        # Create a topology with potential infinite path
        nodes = []
        edges = []

        # Create a chain of 25 networks
        for i in range(25):
            node_id = f"network:net-{i}"
            nodes.append(TopologyNode(
                id=node_id,
                resource_id=f"net-{i}",
                resource_type="network",
                role="network",
                name=f"Network-{i}",
                status="ACTIVE",
                layer="network",
            ))

            if i == 0:
                nodes.append(TopologyNode(
                    id="server:vm-long",
                    resource_id="vm-long",
                    resource_type="server",
                    role="vm",
                    name="long-vm",
                    status="ACTIVE",
                    layer="workload",
                ))
                edges.append(TopologyEdge(
                    id=f"edge-vm-{i}",
                    source="server:vm-long",
                    target=node_id,
                    relationship="attached_to",
                    inferred=False,
                    confidence=1.0,
                ))
            else:
                edges.append(TopologyEdge(
                    id=f"edge-{i-1}-{i}",
                    source=f"network:net-{i-1}",
                    target=node_id,
                    relationship="contains",
                    inferred=False,
                    confidence=1.0,
                ))

        engine.set_topology(nodes, edges)
        result = engine.find_internet_path("vm-long")

        # Should not find internet (no path)
        assert result.found is False
        # Should have partial path
        assert len(result.path) > 0
