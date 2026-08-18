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
