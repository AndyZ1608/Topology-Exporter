"""Regression tests for the public API route contract."""

from app.main import app


def test_expected_api_v1_routes_are_registered_once():
    paths = app.openapi()["paths"]

    for expected_path in (
        "/api/v1/health",
        "/api/v1/sync/status",
        "/api/v1/projects",
        "/api/v1/topology",
        "/api/v1/nodes/{node_id}",
        "/api/v1/path/{server_id}/internet",
    ):
        assert expected_path in paths


def test_routes_do_not_repeat_the_api_prefix():
    paths = app.openapi()["paths"]

    assert not any("/api/v1/api/v1" in path for path in paths)
