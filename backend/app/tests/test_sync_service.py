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
