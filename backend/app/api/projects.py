"""
Projects API endpoints.
"""
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.services.sync_service import get_sync_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects():
    """
    List all OpenStack projects.

    Returns a list of projects with their metadata.
    """
    sync_service = get_sync_service()

    if not sync_service.current_topology:
        # Trigger a sync first
        await run_in_threadpool(sync_service.sync)

    if not sync_service.current_topology:
        return {"projects": []}

    # Extract unique projects from topology
    projects_map = {}
    for node in sync_service.current_topology.nodes:
        if node.project_id and node.project_id not in projects_map:
            projects_map[node.project_id] = {
                "id": node.project_id,
                "name": node.project_name or node.project_id,
            }

    projects = list(projects_map.values())
    projects.sort(key=lambda p: p["name"])

    return {
        "projects": projects,
        "total": len(projects),
    }


@router.get("/{project_id}")
async def get_project(project_id: str):
    """
    Get a specific project by ID.
    """
    sync_service = get_sync_service()

    if not sync_service.current_topology:
        return {"error": "No topology available"}

    # Find the project
    for node in sync_service.current_topology.nodes:
        if node.project_id == project_id:
            return {
                "id": project_id,
                "name": node.project_name or project_id,
                "resource_count": sum(
                    1 for n in sync_service.current_topology.nodes
                    if n.project_id == project_id
                ),
            }

    raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
