"""
Unit tests for the relationship engine.
"""
import pytest
from app.topology.relationship_engine import RelationshipEngine
from app.schemas.topology import TopologyEdge


class TestRelationshipEngine:
    """Tests for RelationshipEngine."""

    @pytest.fixture
    def engine(self):
        return RelationshipEngine()

    def test_add_server_port_relationship(self, engine):
        """Test adding a server-to-network attachment."""
        edge = engine.add_server_port_relationship(
            server_id="server-1",
            port_id="port-1",
            network_id="network-1",
        )

        assert edge.id == "edge-server-1-port-1"
        assert edge.source == "server:server-1"
        assert edge.target == "network:network-1"
        assert edge.relationship == "attached_to"
        assert edge.inferred is False
        assert edge.confidence == 1.0
        assert edge.properties.port_id == "port-1"

    def test_add_subnet_relationship(self, engine):
        """Test adding a network-to-subnet containment."""
        edge = engine.add_subnet_relationship(
            network_id="network-1",
            subnet_id="subnet-1",
        )

        assert edge.id == "edge-network-1-subnet-1"
        assert edge.source == "network:network-1"
        assert edge.target == "subnet:subnet-1"
        assert edge.relationship == "contains"

    def test_add_router_interface_relationship(self, engine):
        """Test adding a router-to-network interface."""
        edge = engine.add_router_interface_relationship(
            router_id="router-1",
            network_id="network-1",
            port_id="router-port-1",
        )

        assert edge.id == "edge-router-router-1-network-1"
        assert edge.source == "network:network-1"
        assert edge.target == "router:router-1"
        assert edge.relationship == "router_interface"
        assert edge.properties.port_id == "router-port-1"

    def test_add_external_gateway_relationship(self, engine):
        """Test adding a router-to-external-network gateway."""
        edge = engine.add_external_gateway_relationship(
            router_id="router-1",
            external_network_id="ext-net-1",
        )

        assert edge.id == "edge-external-router-1-ext-net-1"
        assert edge.source == "router:router-1"
        assert edge.target == "network:ext-net-1"
        assert edge.relationship == "external_gateway"

    def test_add_floating_ip_relationship(self, engine):
        """Test adding a server-to-floating-IP relationship."""
        edge = engine.add_floating_ip_relationship(
            server_id="server-1",
            floating_ip="203.0.113.10",
            fixed_ip="10.0.0.5",
            port_id="port-1",
        )

        assert edge.source == "server:server-1"
        assert edge.target == "floatingip:203-0-113-10"
        assert edge.relationship == "floating_ip"
        assert edge.properties.floating_ip == "203.0.113.10"
        assert edge.properties.fixed_ip == "10.0.0.5"

    def test_add_internet_relationship(self, engine):
        """Test adding an external-network-to-Internet relationship."""
        edge = engine.add_internet_relationship(
            external_network_id="ext-net-1",
            confidence=0.95,
        )

        assert edge.id == "edge-internet-ext-net-1"
        assert edge.source == "network:ext-net-1"
        assert edge.target == "internet"
        assert edge.relationship == "internet_uplink"
        assert edge.inferred is True
        assert edge.confidence == 0.95

    def test_add_inferred_firewall_relationship(self, engine):
        """Test adding an inferred firewall relationship."""
        edge = engine.add_inferred_firewall_relationship(
            vm_server_id="vm-1",
            firewall_server_id="fw-1",
            network_id="net-1",
            confidence=0.8,
        )

        assert edge.id == "edge-inferred-vm-1-fw-1"
        assert edge.source == "network:net-1"
        assert edge.target == "server:fw-1"
        assert edge.relationship == "egress_via"
        assert edge.inferred is True
        assert edge.confidence == 0.8

    def test_add_ha_group_relationship(self, engine):
        """Test adding a firewall-to-HA-group relationship."""
        edge = engine.add_ha_group_relationship(
            ha_group_id="PAN-HA",
            member_id="PAN01",
        )

        assert edge.id == "edge-ha-PAN-HA-PAN01"
        assert edge.source == "server:PAN01"
        assert edge.target == "ha-group:PAN-HA"
        assert edge.relationship == "ha_member"

    def test_get_server_network(self, engine):
        """Test getting the network a server is attached to."""
        engine.add_server_port_relationship("server-1", "port-1", "network-1")
        engine.add_server_port_relationship("server-1", "port-2", "network-2")

        network = engine.get_server_network("server-1")
        assert network == "network-1"

    def test_get_network_servers(self, engine):
        """Test getting all servers attached to a network."""
        engine.add_server_port_relationship("server-1", "port-1", "network-1")
        engine.add_server_port_relationship("server-2", "port-2", "network-1")

        servers = engine.get_network_servers("network-1")
        assert "server-1" in servers
        assert "server-2" in servers

    def test_get_upstream_nodes(self, engine):
        """Test getting upstream nodes."""
        engine.add_server_port_relationship("server-1", "port-1", "network-1")
        engine.add_subnet_relationship("network-1", "subnet-1")

        upstream = engine.get_upstream_nodes("network:network-1")
        assert "server:server-1" in upstream

    def test_get_downstream_nodes(self, engine):
        """Test getting downstream nodes."""
        engine.add_server_port_relationship("server-1", "port-1", "network-1")
        engine.add_subnet_relationship("network-1", "subnet-1")

        downstream = engine.get_downstream_nodes("network:network-1")
        assert "subnet:subnet-1" in downstream

    def test_get_edges(self, engine):
        """Test getting all edges."""
        engine.add_server_port_relationship("server-1", "port-1", "network-1")
        engine.add_subnet_relationship("network-1", "subnet-1")

        edges = engine.get_edges()
        assert len(edges) == 2

    def test_reset(self, engine):
        """Test resetting the engine."""
        engine.add_server_port_relationship("server-1", "port-1", "network-1")
        engine.reset()

        assert len(engine.get_edges()) == 0
        assert engine.get_server_network("server-1") is None
