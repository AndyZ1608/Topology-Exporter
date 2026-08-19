"""Regression tests for topology synchronization state."""

from app.services import sync_service as sync_module
from app.schemas.topology import TopologyResponse


def test_demo_sync_builds_a_valid_snapshot(monkeypatch):
    monkeypatch.setattr(sync_module.settings, "DEMO_MODE", True)
    service = sync_module.TopologySyncService()

    status = service.sync()

    assert status.status == "success"
    assert status.partial is False
    assert status.node_count > 0
    assert service.current_topology is not None


def test_partial_sync_preserves_previous_complete_snapshot(monkeypatch):
    monkeypatch.setattr(sync_module.settings, "DEMO_MODE", True)
    service = sync_module.TopologySyncService()
    service.sync()
    complete_snapshot = service.current_topology

    monkeypatch.setattr(sync_module.settings, "DEMO_MODE", False)
    monkeypatch.setattr(
        service,
        "_sync_from_openstack",
        lambda: (TopologyResponse(nodes=[], edges=[]), ["nova"]),
    )

    status = service.sync()

    assert status.status == "partial"
    assert status.failed_collectors == ["nova"]
    assert service.current_topology is complete_snapshot


def test_summary_and_search_use_normalized_snapshot(monkeypatch):
    monkeypatch.setattr(sync_module.settings, "DEMO_MODE", True)
    service = sync_module.TopologySyncService()
    service.sync()

    summary = service.get_cloud_summary()
    fixed_ip_results = service.search("10.0.30.15")
    floating_ip_results = service.search("203.0.113.101")
    cidr_results = service.search("10.0.30.0/24")

    assert summary["projects"] == 1
    assert summary["servers"] > 0
    assert summary["networks"] == 4
    assert summary["routers"] == 1
    assert any(result["name"] == "monitor01" for result in fixed_ip_results)
    assert any(result["name"] == "monitor01" for result in floating_ip_results)
    assert any(result["name"] == "VLAN30-Monitor" for result in cidr_results)


def test_openstack_sync_uses_system_identity_then_one_scope_per_project(monkeypatch):
    from app.openstack.connection import connection_manager

    system_connection = object()
    project_connections = []
    captured_graph = {}

    projects = {
        "project-1": {"id": "project-1", "name": "NOC", "domain_id": "domain-mbfs", "enabled": True},
        "project-2": {"id": "project-2", "name": "APP", "domain_id": "domain-mbfs", "enabled": True},
    }

    class FakeIdentityCollector:
        def __init__(self, connection=None):
            if connection is not None:
                assert connection is system_connection

        def find_domain(self, name):
            assert name == "MBFS"
            return {"id": "domain-mbfs", "name": "MBFS", "enabled": True}

        def collect_projects(self, domain_id):
            assert domain_id == "domain-mbfs"
            return projects

    class FakeComputeCollector:
        def __init__(self, connection=None):
            self.connection = connection

        def collect_servers(self):
            project_id = self.connection["project_id"]
            return {f"server-{project_id}": {"id": f"server-{project_id}"}}

    class FakeNetworkCollector:
        def __init__(self, connection=None):
            self.connection = connection

        def collect_all(self):
            project_id = self.connection["project_id"]
            failures = ["trunks"] if project_id == "project-2" else []
            return {
                "networks": {f"net-{project_id}": {"id": f"net-{project_id}"}},
                "subnets": {}, "ports": {}, "routers": {},
                "floating_ips": {}, "trunks": {}, "security_groups": {},
                "failed_resources": failures,
            }

    class FakeGraphBuilder:
        def build_from_openstack(self, **kwargs):
            captured_graph.update(kwargs)
            return TopologyResponse(nodes=[], edges=[])

    def project_connection(project):
        connection = {"project_id": project["id"]}
        project_connections.append(connection)
        return connection

    monkeypatch.setattr(sync_module.settings, "TOPOLOGY_DOMAIN_NAME", "MBFS")
    monkeypatch.setattr(connection_manager, "get_system_connection", lambda: system_connection)
    monkeypatch.setattr(connection_manager, "get_project_connection", project_connection)
    monkeypatch.setattr(sync_module, "IdentityCollector", FakeIdentityCollector)
    monkeypatch.setattr(sync_module, "ComputeCollector", FakeComputeCollector)
    monkeypatch.setattr(sync_module, "NetworkCollector", FakeNetworkCollector)

    service = sync_module.TopologySyncService()
    service._graph_builder = FakeGraphBuilder()
    _, failures = service._sync_from_openstack()

    assert [connection["project_id"] for connection in project_connections] == [
        "project-1", "project-2"
    ]
    assert set(captured_graph["servers"]) == {
        "server-project-1", "server-project-2"
    }
    assert set(captured_graph["networks"]) == {
        "net-project-1", "net-project-2"
    }
    assert failures == ["neutron.trunks:project-2"]
