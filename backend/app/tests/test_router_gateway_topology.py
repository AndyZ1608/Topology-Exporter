"""Router gateway and external-network presentation acceptance tests."""

from app.services.sync_service import TopologySyncService
from app.topology.graph_builder import GraphBuilder


def _network(network_id: str, external: bool = False) -> dict:
    return {
        "id": network_id,
        "name": "external-2085" if external else network_id.upper(),
        "project_id": "project-1",
        "router:external": external,
        "provider:network_type": "flat" if external else "vxlan",
        "provider:physical_network": "physnet1" if external else None,
        "provider:segmentation_id": None,
        "shared": external,
        "status": "ACTIVE",
        "tags": [],
    }


def _build_gateway_topology(external_fixed_ips: list[dict] | None = None):
    networks = {
        "net-10": _network("net-10"),
        "net-20": _network("net-20"),
        "net-30": _network("net-30"),
        "external": _network("external", external=True),
    }
    subnets = {
        "subnet-10": {"id": "subnet-10", "name": "WEB", "network_id": "net-10", "cidr": "10.0.10.0/24", "gateway_ip": "10.0.10.254"},
        "subnet-20": {"id": "subnet-20", "name": "APP", "network_id": "net-20", "cidr": "10.0.20.0/24", "gateway_ip": "10.0.20.254"},
        "subnet-30": {"id": "subnet-30", "name": "DB", "network_id": "net-30", "cidr": "10.0.30.0/24", "gateway_ip": "10.0.30.254"},
        "external-subnet": {"id": "external-subnet", "name": "WAN", "network_id": "external", "cidr": "10.1.85.0/24", "gateway_ip": "10.1.85.1"},
    }
    ports = {}
    interfaces = []
    owners = [
        "network:router_interface",
        "network:router_interface_distributed",
        "network:ha_router_replicated_interface",
    ]
    for suffix, gateway_ip, owner in zip(("10", "20", "30"), ("10.0.10.1", "10.0.20.1", "10.0.30.1"), owners):
        port_id = f"router-if-{suffix}"
        ports[port_id] = {
            "id": port_id, "network_id": f"net-{suffix}", "device_id": "router-1",
            "device_owner": owner, "device_owner_category": "router_interface",
            "fixed_ips": [{"subnet_id": f"subnet-{suffix}", "ip_address": gateway_ip}],
        }
        interfaces.append({"port_id": port_id, "network_id": f"net-{suffix}"})

    ports["router-gateway"] = {
        "id": "router-gateway", "network_id": "external", "device_id": "router-1",
        "device_owner": "network:router_gateway", "device_owner_category": "router_gateway",
        "fixed_ips": [{"subnet_id": "external-subnet", "ip_address": "10.1.85.34"}],
    }
    ports["pan-internal"] = {
        "id": "pan-internal", "network_id": "net-20", "device_id": "pan-1",
        "device_owner_category": "compute", "fixed_ips": [{"subnet_id": "subnet-20", "ip_address": "10.0.20.3"}],
        "mac_address": "fa:16:3e:00:20:03", "security_groups": [], "tags": [],
    }
    ports["pan-wan"] = {
        "id": "pan-wan", "network_id": "external", "device_id": "pan-1",
        "device_owner_category": "compute", "fixed_ips": [{"subnet_id": "external-subnet", "ip_address": "10.1.85.193"}],
        "mac_address": "fa:16:3e:01:85:93", "security_groups": [], "tags": [],
    }
    routers = {
        "router-1": {
            "id": "router-1", "name": "DBA", "project_id": "project-1", "status": "ACTIVE",
            "interfaces": interfaces,
            "external_gateway_info": {
                "network_id": "external", "enable_snat": True,
                "external_fixed_ips": external_fixed_ips if external_fixed_ips is not None else [
                    {"subnet_id": "external-subnet", "ip_address": "10.1.85.34"}
                ],
            },
        },
        "internal-router": {
            "id": "internal-router", "name": "Internal", "project_id": "project-1", "status": "ACTIVE",
            "interfaces": [], "external_gateway_info": None,
        },
    }
    topology = GraphBuilder().build_from_openstack(
        projects={"project-1": {"id": "project-1", "name": "Project One"}},
        servers={"pan-1": {
            "id": "pan-1", "name": "PAN01", "project_id": "project-1", "status": "ACTIVE",
            "metadata": {"device_role": "firewall"}, "tags": [],
        }},
        networks=networks, subnets=subnets, ports=ports, routers=routers,
        floating_ips={}, trunks={}, security_groups={},
    )
    return topology


def test_router_gateway_model_and_direct_internet_presentation():
    topology = _build_gateway_topology()
    nodes = {node.id: node for node in topology.nodes}
    router = nodes["router:router-1"]

    assert "network:external" in nodes  # retained normalized infrastructure truth
    assert router.properties.external_gateway == {
        "network_id": "external", "network_name": "external-2085",
        "enable_snat": True, "subnet_id": "external-subnet",
        "subnet_name": "WAN", "subnet_cidr": "10.1.85.0/24",
        "ip_address": "10.1.85.34",
        "fixed_ips": [{
            "subnet_id": "external-subnet", "subnet_name": "WAN",
            "subnet_cidr": "10.1.85.0/24", "ip_address": "10.1.85.34",
        }],
    }
    direct = next(
        edge for edge in topology.edges
        if edge.source == "router:router-1" and edge.target == "internet"
    )
    assert direct.properties.ip_address == "10.1.85.34"
    assert direct.properties.external_network_name == "external-2085"
    assert direct.properties.connection_kind == "router_external_gateway"


def test_each_internal_router_edge_has_its_actual_port_ip():
    topology = _build_gateway_topology()
    gateway_by_network = {
        edge.source: edge.properties.gateway_ip
        for edge in topology.edges
        if edge.relationship == "router_interface" and edge.target == "router:router-1"
    }
    assert gateway_by_network == {
        "network:net-10": "10.0.10.1",
        "network:net-20": "10.0.20.1",
        "network:net-30": "10.0.30.1",
    }


def test_gateway_port_is_used_when_external_fixed_ips_are_missing():
    topology = _build_gateway_topology(external_fixed_ips=[])
    router = next(node for node in topology.nodes if node.id == "router:router-1")
    assert router.properties.external_gateway["ip_address"] == "10.1.85.34"


def test_router_without_external_gateway_has_no_internet_edge():
    topology = _build_gateway_topology()
    assert not any(
        edge.source == "router:internal-router" and edge.target == "internet"
        for edge in topology.edges
    )


def test_external_vm_keeps_one_node_and_gets_real_wan_uplink():
    topology = _build_gateway_topology()
    pan_nodes = [node for node in topology.nodes if node.id == "server:pan-1"]
    assert len(pan_nodes) == 1
    assert set(pan_nodes[0].properties.interfaces) == {"pan-internal", "pan-wan"}
    uplink = next(
        edge for edge in topology.edges
        if edge.source == "server:pan-1" and edge.target == "internet"
    )
    assert uplink.properties.ip_address == "10.1.85.193"
    assert uplink.properties.external_network_id == "external"
    assert uplink.properties.connection_kind == "vm_external_interface"


def test_external_and_gateway_values_remain_searchable():
    service = TopologySyncService()
    service._current_topology = _build_gateway_topology()

    assert {node["id"] for node in service.search("external-2085")} >= {
        "network:external", "router:router-1", "server:pan-1"
    }
    assert {node["id"] for node in service.search("10.1.85.34")} == {"router:router-1"}
    assert {node["id"] for node in service.search("10.0.20.1")} == {"router:router-1"}
    assert service.get_topology(search="10.0.20.1")["metadata"]["matched_node_ids"] == [
        "router:router-1"
    ]
