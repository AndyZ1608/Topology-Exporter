"""Acceptance-style unit tests for the required topology reconstruction cases."""

from app.services.sync_service import TopologySyncService
from app.topology.graph_builder import GraphBuilder


def _build_required_scenarios():
    builder = GraphBuilder()
    projects = {
        "project-a": {"id": "project-a", "name": "Project A"},
        "project-b": {"id": "project-b", "name": "Project B"},
    }
    networks = {
        "net-a": {
            "id": "net-a", "name": "WEB-PROD", "project_id": "project-a",
            "router:external": False, "provider:network_type": "vlan",
            "provider:physical_network": "physnet1", "provider:segmentation_id": 100,
            "shared": False, "status": "ACTIVE", "tags": [],
        },
        "net-b": {
            "id": "net-b", "name": "APP-PROD", "project_id": "project-a",
            "router:external": False, "provider:network_type": "vxlan",
            "provider:physical_network": None, "provider:segmentation_id": 5010,
            "shared": False, "status": "ACTIVE", "tags": [],
        },
        "shared-net": {
            "id": "shared-net", "name": "SHARED-SERVICES", "project_id": "project-b",
            "router:external": False, "provider:network_type": "vlan",
            "provider:physical_network": "physnet1", "provider:segmentation_id": 200,
            "shared": True, "status": "ACTIVE", "tags": [],
        },
        "public": {
            "id": "public", "name": "PUBLIC-NET", "project_id": None,
            "router:external": True, "provider:network_type": "flat",
            "provider:physical_network": "public", "provider:segmentation_id": None,
            "shared": True, "status": "ACTIVE", "tags": [],
        },
    }
    subnets = {
        "subnet-a": {"id": "subnet-a", "name": "WEB", "network_id": "net-a", "project_id": "project-a", "cidr": "10.10.10.0/24", "gateway_ip": "10.10.10.1", "tags": []},
        "subnet-b": {"id": "subnet-b", "name": "APP", "network_id": "net-b", "project_id": "project-a", "cidr": "10.10.20.0/24", "gateway_ip": "10.10.20.1", "tags": []},
    }
    servers = {
        "vm-a": {"id": "vm-a", "name": "web-01", "project_id": "project-a", "status": "ACTIVE", "metadata": {}, "tags": [], "flavor_name": "m1.small", "availability_zone": "nova", "host": "compute-01"},
        "vm-b": {"id": "vm-b", "name": "shared-client", "project_id": "project-b", "status": "ACTIVE", "metadata": {}, "tags": [], "flavor_name": "m1.small"},
        "vm-c": {"id": "vm-c", "name": "shared-client-a", "project_id": "project-a", "status": "ACTIVE", "metadata": {}, "tags": [], "flavor_name": "m1.small"},
    }
    ports = {
        "port-a1": {"id": "port-a1", "network_id": "net-a", "device_id": "vm-a", "device_owner_category": "compute", "fixed_ips": [{"ip_address": "10.10.10.20", "subnet_id": "subnet-a"}], "mac_address": "fa:16:3e:00:00:01", "security_groups": ["sg-web"], "tags": []},
        "port-a2": {"id": "port-a2", "network_id": "net-b", "device_id": "vm-a", "device_owner_category": "compute", "fixed_ips": [{"ip_address": "10.10.20.20", "subnet_id": "subnet-b"}], "mac_address": "fa:16:3e:00:00:02", "security_groups": [], "tags": []},
        "port-b1": {"id": "port-b1", "network_id": "shared-net", "device_id": "vm-b", "device_owner_category": "compute", "fixed_ips": [{"ip_address": "10.20.0.8"}], "mac_address": "fa:16:3e:00:00:03", "security_groups": [], "tags": []},
        "port-c1": {"id": "port-c1", "network_id": "shared-net", "device_id": "vm-c", "device_owner_category": "compute", "fixed_ips": [{"ip_address": "10.20.0.9"}], "mac_address": "fa:16:3e:00:00:04", "security_groups": [], "tags": []},
    }
    routers = {
        "router-1": {
            "id": "router-1", "name": "edge-router", "project_id": "project-a", "status": "ACTIVE",
            "interfaces": [{"port_id": "rif-a", "network_id": "net-a"}, {"port_id": "rif-b", "network_id": "net-b"}],
            "external_gateway_info": {"network_id": "public", "enable_snat": True},
        }
    }
    topology = builder.build_from_openstack(
        projects=projects, servers=servers, networks=networks, subnets=subnets,
        ports=ports, routers=routers,
        floating_ips={"fip-a": {"id": "fip-a", "port_id": "port-a1", "fixed_ip_address": "10.10.10.20", "floating_ip_address": "203.0.113.20"}},
        trunks={}, security_groups={"sg-web": {"id": "sg-web", "name": "web-access"}},
    )
    return builder, topology


def test_router_path_two_nics_floating_ip_and_two_internal_networks():
    builder, topology = _build_required_scenarios()
    node_by_id = {node.id: node for node in topology.nodes}
    edge_pairs = {(edge.source, edge.target) for edge in topology.edges}

    assert builder.find_internet_path("vm-a")["path"] == [
        "server:vm-a", "network:net-a", "router:router-1", "internet"
    ]
    assert sum(edge.source == "server:vm-a" and edge.relationship == "attached_to" for edge in topology.edges) == 2
    assert sum(node.id == "server:vm-a" for node in topology.nodes) == 1
    assert node_by_id["server:vm-a"].properties.floating_ips == ["203.0.113.20"]
    assert set(node_by_id["server:vm-a"].properties.interfaces) == {"port-a1", "port-a2"}
    assert node_by_id["server:vm-a"].properties.security_groups == ["web-access"]
    assert ("network:net-a", "router:router-1") in edge_pairs
    assert ("network:net-b", "router:router-1") in edge_pairs
    assert not {"subnet", "trunk", "ha_group", "firewall", "firewall_member"}.intersection(
        node.resource_type for node in topology.nodes
    )
    port_edge = next(edge for edge in topology.edges if edge.properties.port_id == "port-a1")
    assert port_edge.properties.fixed_ip == "10.10.10.20"
    assert port_edge.properties.network_id == "net-a"
    assert port_edge.properties.mac_address == "fa:16:3e:00:00:01"


def test_shared_network_survives_project_filter_and_vlan_is_normalized():
    _, topology = _build_required_scenarios()
    node_by_id = {node.id: node for node in topology.nodes}
    vlan = node_by_id["network:net-a"].properties
    assert (vlan.provider_network_type, vlan.provider_physical_network, vlan.provider_segmentation_id) == ("vlan", "physnet1", 100)

    service = TopologySyncService()
    service._current_topology = topology
    filtered_ids = {node["id"] for node in service.get_topology(project_ids=["project-a"])["nodes"]}
    assert "network:shared-net" in filtered_ids
    assert "network:public" in filtered_ids
    selected_servers = {node_id for node_id in filtered_ids if node_id.startswith("server:")}
    assert selected_servers == {"server:vm-a", "server:vm-c"}


def test_trunk_subport_is_folded_into_one_multinic_vm():
    builder = GraphBuilder()
    network = lambda network_id: {
        "id": network_id, "name": network_id, "project_id": "project-a",
        "router:external": False, "provider:network_type": "vlan",
        "provider:physical_network": "physnet1", "provider:segmentation_id": 100,
        "shared": False, "status": "ACTIVE", "tags": [],
    }
    topology = builder.build_from_openstack(
        projects={"project-a": {"id": "project-a", "name": "Project A"}},
        servers={"appliance": {"id": "appliance", "name": "router-vm", "project_id": "project-a", "status": "ACTIVE", "metadata": {"device_role": "router"}, "tags": []}},
        networks={"net-a": network("net-a"), "net-b": network("net-b")},
        subnets={},
        ports={
            "parent": {"id": "parent", "network_id": "net-a", "device_id": "appliance", "device_owner_category": "compute", "fixed_ips": [{"ip_address": "10.0.1.2"}], "mac_address": "fa:16:3e:00:01:01", "security_groups": [], "tags": []},
            "subport": {"id": "subport", "network_id": "net-b", "device_id": "", "device_owner_category": "other", "fixed_ips": [{"ip_address": "10.0.2.2"}], "mac_address": "fa:16:3e:00:02:01", "security_groups": [], "tags": []},
        },
        routers={}, floating_ips={},
        trunks={"trunk-1": {"id": "trunk-1", "port_id": "parent", "sub_ports": [{"port_id": "subport", "segmentation_type": "vlan", "segmentation_id": 200}]}},
        security_groups={},
    )

    servers = [node for node in topology.nodes if node.resource_type == "server"]
    attachments = [edge for edge in topology.edges if edge.relationship == "attached_to"]
    assert len(servers) == 1
    assert set(servers[0].properties.interfaces) == {"parent", "subport"}
    assert {edge.target for edge in attachments} == {"network:net-a", "network:net-b"}
    assert not any(node.resource_type == "trunk" for node in topology.nodes)
