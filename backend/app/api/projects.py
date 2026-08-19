"""Selectable Keystone projects API."""

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.services.sync_service import get_sync_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects():
    """List only validated projects belonging to the topology domain."""
    sync_service = get_sync_service()
    if not sync_service.current_topology:
        await run_in_threadpool(sync_service.sync)

    projects = sync_service.get_selectable_projects()
    return {"projects": projects, "total": len(projects)}


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Return one selectable project; dependency-owner projects are excluded."""
    sync_service = get_sync_service()
    project = sync_service.get_selectable_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    topology = sync_service.current_topology
    return {
        "id": project["id"],
        "name": project.get("name") or project["id"],
        "domain_id": project.get("domain_id"),
        "resource_count": sum(
            1 for node in (topology.nodes if topology else [])
            if node.project_id == project_id
        ),
    }
