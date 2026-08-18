"""Tests for explicit external and OpenStack-hosted firewall mappings."""

from app.topology.firewall_config import FirewallMapping, load_firewall_mappings
from app.topology.graph_builder import GraphBuilder


def test_firewall_mapping_file_is_validated(tmp_path):
    config_path = tmp_path / "firewalls.yaml"
    config_path.write_text(
        """
firewalls:
  - id: dc-pa-ha
    name: DC Palo Alto HA
    vendor: paloalto
    type: external
    members: [PAN01, PAN02]
    upstream:
      external_network: PUBLIC-NET
    downstream:
      physical_network: physnet1
""",
        encoding="utf-8",
    )

    mappings = load_firewall_mappings(config_path)

    assert len(mappings) == 1
    assert mappings[0].id == "dc-pa-ha"
    assert mappings[0].members == ["PAN01", "PAN02"]


def test_external_firewall_is_injected_only_from_explicit_mapping():
    builder = GraphBuilder()
    builder.firewall_mappings = [
        FirewallMapping.model_validate({
            "id": "dc-pa-ha",
            "name": "DC Palo Alto HA",
            "vendor": "paloalto",
            "type": "external",
            "members": ["PAN01", "PAN02"],
            "upstream": {"external_network": "PUBLIC-NET"},
            "downstream": {"physical_network": "physnet1"},
        })
    ]
    networks = {
        "internal": {
            "id": "internal",
            "name": "WEB-PROD",
            "project_id": "project-1",
            "router:external": False,
            "provider:network_type": "vlan",
            "provider:physical_network": "physnet1",
            "provider:segmentation_id": 100,
            "shared": False,
            "status": "ACTIVE",
            "tags": [],
        },
        "external": {
            "id": "external",
            "name": "PUBLIC-NET",
            "project_id": None,
            "router:external": True,
            "provider:network_type": "flat",
            "provider:physical_network": "public",
            "provider:segmentation_id": None,
            "shared": True,
            "status": "ACTIVE",
            "tags": [],
        },
    }

    topology = builder.build_from_openstack(
        projects={"project-1": {"id": "project-1", "name": "WEB"}},
        servers={
            "vm-1": {
                "id": "vm-1",
                "name": "web-prod-01",
                "project_id": "project-1",
                "status": "ACTIVE",
                "metadata": {},
                "tags": [],
                "flavor_name": "m1.small",
            }
        },
        networks=networks,
        subnets={},
        ports={
            "port-1": {
                "id": "port-1",
                "network_id": "internal",
                "device_id": "vm-1",
                "device_owner_category": "compute",
                "fixed_ips": [{"ip_address": "10.10.10.20"}],
                "mac_address": "fa:16:3e:00:00:01",
                "security_groups": [],
                "tags": [],
            }
        },
        routers={},
        floating_ips={},
        trunks={},
        security_groups={},
    )

    node_ids = {node.id for node in topology.nodes}
    edge_pairs = {(edge.source, edge.target) for edge in topology.edges}
    assert "firewall:dc-pa-ha" in node_ids
    assert "firewall-member:dc-pa-ha:pan01" in node_ids
    assert "firewall-member:dc-pa-ha:pan02" in node_ids
    assert ("network:internal", "firewall:dc-pa-ha") in edge_pairs
    assert ("firewall:dc-pa-ha", "network:external") in edge_pairs

    path = builder.find_internet_path("vm-1")
    assert path["found"] is True
    assert path["path"] == [
        "server:vm-1",
        "network:internal",
        "firewall:dc-pa-ha",
        "network:external",
        "internet",
    ]
