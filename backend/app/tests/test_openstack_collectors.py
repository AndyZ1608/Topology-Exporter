"""Project-scoped Nova/Neutron/Keystone collector regression tests."""

from types import SimpleNamespace

from app.openstack.compute_collector import ComputeCollector
from app.openstack.identity_collector import IdentityCollector
from app.openstack.network_collector import NetworkCollector


def test_compute_server_list_never_requests_all_projects():
    calls = []

    class ComputeProxy:
        def servers(self, **kwargs):
            calls.append(kwargs)
            return []

    ComputeCollector(SimpleNamespace(compute=ComputeProxy())).collect_servers()
    assert calls == [{}]


def test_identity_projects_are_queried_and_filtered_by_domain():
    calls = []
    domain = SimpleNamespace(id="domain-mbfs", name="MBFS", enabled=True)
    project = SimpleNamespace(
        id="project-1", name="NOC", domain_id="domain-mbfs",
        enabled=True, description=None,
    )

    class IdentityProxy:
        def domains(self, **kwargs):
            assert kwargs == {"name": "MBFS"}
            return [domain]

        def projects(self, **kwargs):
            calls.append(kwargs)
            return [project, SimpleNamespace(
                id="other", name="Other", domain_id="other-domain",
                enabled=True, description=None,
            )]

    collector = IdentityCollector(SimpleNamespace(identity=IdentityProxy()))
    discovered_domain = collector.find_domain("MBFS")
    projects = collector.collect_projects(discovered_domain["id"])

    assert calls == [{"domain_id": "domain-mbfs"}]
    assert set(projects) == {"project-1"}


def test_trunk_failure_isolated_from_other_network_resources(caplog):
    network = SimpleNamespace(
        id="net-1", name="VLAN10_AV", project_id="project-1",
        is_router_external=False, provider_network_type="vlan",
        provider_physical_network="physnet1", provider_segmentation_id=10,
        is_shared=False, status="ACTIVE", subnet_ids=["subnet-1"], tags=[],
    )
    subnet = SimpleNamespace(
        id="subnet-1", name="VLAN10_AV", network_id="net-1",
        project_id="project-1", cidr="10.0.10.0/24", gateway_ip="10.0.10.1",
        ip_version=4, is_dhcp_enabled=True, dns_nameservers=[],
        allocation_pools=[], tags=[],
    )
    port = SimpleNamespace(
        id="subport-1", name="PAN01-subport-vlan10", network_id="net-1",
        project_id="project-1", device_id="", device_owner="",
        mac_address="fa:16:3e:00:00:10",
        fixed_ips=[{"ip_address": "10.0.10.3", "subnet_id": "subnet-1"}],
        status="ACTIVE", binding_host_id=None, security_group_ids=[], tags=[],
    )

    class NetworkProxy:
        def networks(self): return [network]
        def subnets(self): return [subnet]
        def ports(self): return [port]
        def routers(self): return []
        def ips(self): return []
        def trunks(self): raise AttributeError("trunk extension unavailable")
        def security_groups(self): return []

    result = NetworkCollector(SimpleNamespace(network=NetworkProxy())).collect_all()

    assert set(result["networks"]) == {"net-1"}
    assert set(result["subnets"]) == {"subnet-1"}
    assert set(result["ports"]) == {"subport-1"}
    assert result["trunks"] == {}
    assert result["failed_resources"] == ["trunks"]
    assert "Traceback" in caplog.text


def test_trunk_parent_and_subports_are_normalized():
    trunk = SimpleNamespace(
        id="trunk-1", name="PAN01-trunk", project_id="project-1",
        status="ACTIVE", port_id="parent-port",
        sub_ports=[{
            "port_id": "subport-1",
            "segmentation_type": "vlan",
            "segmentation_id": 10,
        }],
    )

    class NetworkProxy:
        def networks(self): return []
        def subnets(self): return []
        def ports(self): return []
        def routers(self): return []
        def ips(self): return []
        def trunks(self): return [trunk]
        def security_groups(self): return []

    result = NetworkCollector(SimpleNamespace(network=NetworkProxy())).collect_all()
    assert result["trunks"]["trunk-1"]["port_id"] == "parent-port"
    assert result["trunks"]["trunk-1"]["sub_ports"] == [{
        "port_id": "subport-1",
        "segmentation_type": "vlan",
        "segmentation_id": 10,
    }]
