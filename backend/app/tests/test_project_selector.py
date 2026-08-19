"""Project selector source-of-truth regression tests."""

from fastapi.testclient import TestClient

import app.api.projects as projects_api
import app.api.inventory as inventory_api
from app.main import app
from app.schemas.topology import (
    NodeProperties,
    TopologyEdge,
    TopologyNode,
    TopologyResponse,
)
from app.services.sync_service import TopologySyncService


ADMIN_PROJECT_ID = "3b1cbc5fb9e14c1498b97c0196522949"
MBFS_DOMAIN_ID = "eb2be5b37ae84e9ab743f0119f370f02"
DBA_PROJECT_ID = "dba-project-id"


def test_projects_api_excludes_external_resource_owner_outside_mbfs(monkeypatch):
    service = TopologySyncService()
    service._selectable_projects = {
        DBA_PROJECT_ID: {
            "id": DBA_PROJECT_ID,
            "name": "DBA",
            "domain_id": MBFS_DOMAIN_ID,
            "enabled": True,
        }
    }
    service._current_topology = TopologyResponse(
        nodes=[
            TopologyNode(
                id="server:dba-vm",
                resource_id="dba-vm",
                resource_type="server",
                role="vm",
                name="DBA-VM",
                project_id=DBA_PROJECT_ID,
                project_name="DBA",
                status="ACTIVE",
                layer="workload",
            ),
            TopologyNode(
                id="network:external-shared",
                resource_id="external-shared",
                resource_type="network",
                role="external_network",
                name="external-shared",
                project_id=ADMIN_PROJECT_ID,
                project_name="admin",
                status="ACTIVE",
                layer="external",
                properties=NodeProperties(is_external=True, is_shared=True),
            ),
        ],
        edges=[
            TopologyEdge(
                id="edge:dba-external",
                source="server:dba-vm",
                target="network:external-shared",
                relationship="attached_to",
            )
        ],
    )
    monkeypatch.setattr(projects_api, "get_sync_service", lambda: service)
    monkeypatch.setattr(inventory_api, "get_sync_service", lambda: service)

    response = TestClient(app).get("/api/v1/projects")

    assert response.status_code == 200
    assert response.json() == {
        "projects": [
            {
                "id": DBA_PROJECT_ID,
                "name": "DBA",
                "domain_id": MBFS_DOMAIN_ID,
                "enabled": True,
            }
        ],
        "total": 1,
    }
    assert ADMIN_PROJECT_ID not in {
        project["id"] for project in response.json()["projects"]
    }

    summary_response = TestClient(app).get(
        f"/api/v1/cloud/summary?project_id={DBA_PROJECT_ID}"
    )
    assert summary_response.status_code == 200
    assert summary_response.json()["projects"] == 1
    assert summary_response.json()["servers"] == 1
    assert summary_response.json()["networks"] == 0
    assert summary_response.json()["routers"] == 0

    # The selector and graph dependencies are intentionally separate: the
    # admin-owned external network remains useful to explain DBA connectivity.
    filtered = service.get_topology(project_ids=[DBA_PROJECT_ID])
    assert {node["id"] for node in filtered["nodes"]} == {
        "server:dba-vm",
        "network:external-shared",
    }


def test_projects_api_rejects_non_selectable_dependency_owner(monkeypatch):
    service = TopologySyncService()
    service._selectable_projects = {
        DBA_PROJECT_ID: {
            "id": DBA_PROJECT_ID,
            "name": "DBA",
            "domain_id": MBFS_DOMAIN_ID,
        }
    }
    monkeypatch.setattr(projects_api, "get_sync_service", lambda: service)

    response = TestClient(app).get(f"/api/v1/projects/{ADMIN_PROJECT_ID}")

    assert response.status_code == 404
