"""Tests for the non-authoritative SQL inventory cache."""

from app.repositories import SnapshotRepository
from app.schemas.topology import NodeProperties, TopologyNode, TopologyResponse


def test_snapshot_round_trip_records_normalized_graph(tmp_path):
    repository = SnapshotRepository(f"sqlite:///{tmp_path / 'cache.db'}")
    topology = TopologyResponse(
        nodes=[TopologyNode(id="internet", resource_id="internet", resource_type="internet", role="internet", name="Internet", layer="internet", properties=NodeProperties())],
        edges=[],
        metadata={"source": "openstack"},
    )

    repository.save(topology)
    restored = repository.load_latest()

    assert restored is not None
    assert restored.nodes[0].id == "internet"
    assert restored.metadata["source"] == "openstack"
