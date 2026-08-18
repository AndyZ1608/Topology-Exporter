"""
Topology API endpoints.
"""
from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool
from typing import Optional

from app.services.sync_service import get_sync_service

router = APIRouter(prefix="/topology", tags=["topology"])


@router.get("")
async def get_topology(
    project_id: Optional[str] = Query(None, description="Filter by project ID(s), comma-separated"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type(s), comma-separated"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in name, ID, project name, or IP"),
    view: str = Query("traffic", description="View mode: traffic, infrastructure, project"),
):
    """
    Get the current topology.

    Supports filtering by:
    - project_id: Filter nodes by project
    - resource_type: Filter by type (server, network, router, etc.)
    - status: Filter by status (ACTIVE, SHUTOFF, ERROR)
    - search: Search across names, IDs, IPs
    - view: traffic (default), infrastructure, project
    """
    sync_service = get_sync_service()

    # Parse comma-separated values
    project_ids = None
    if project_id:
        project_ids = [p.strip() for p in project_id.split(",")]

    resource_types = None
    if resource_type:
        resource_types = [t.strip() for t in resource_type.split(",")]

    return sync_service.get_topology(
        project_ids=project_ids,
        resource_types=resource_types,
        status=status,
        search=search,
        view=view,
    )


@router.get("/full")
async def get_full_topology():
    """
    Get the complete topology without filtering.
    """
    sync_service = get_sync_service()

    if not sync_service.current_topology:
        return {"nodes": [], "edges": [], "error": "No topology available"}

    return {
        "nodes": [n.model_dump() for n in sync_service.current_topology.nodes],
        "edges": [e.model_dump() for e in sync_service.current_topology.edges],
        "metadata": sync_service.current_topology.metadata,
    }


@router.post("/refresh")
async def refresh_topology():
    """
    Trigger an immediate topology refresh.
    """
    sync_service = get_sync_service()
    status = await run_in_threadpool(sync_service.sync, True)
    return status.model_dump()


@router.get("/summary")
async def get_topology_summary():
    """
    Get a summary of the current topology.
    """
    sync_service = get_sync_service()

    if not sync_service.current_topology:
        return {"error": "No topology available"}

    topology = sync_service.current_topology

    # Count by type
    by_type = {}
    by_role = {}
    by_layer = {}
    by_status = {}
    by_project = {}

    for node in topology.nodes:
        # By type
        node_type = node.resource_type
        by_type[node_type] = by_type.get(node_type, 0) + 1

        # By role
        role = node.role
        by_role[role] = by_role.get(role, 0) + 1

        # By layer
        layer = node.layer
        by_layer[layer] = by_layer.get(layer, 0) + 1

        # By status
        status = node.status
        by_status[status] = by_status.get(status, 0) + 1

        # By project
        project = node.project_name or "shared"
        by_project[project] = by_project.get(project, 0) + 1

    # Edge counts
    confirmed_edges = sum(1 for e in topology.edges if not e.inferred)
    inferred_edges = sum(1 for e in topology.edges if e.inferred)

    return {
        "total_nodes": len(topology.nodes),
        "total_edges": len(topology.edges),
        "confirmed_edges": confirmed_edges,
        "inferred_edges": inferred_edges,
        "by_type": by_type,
        "by_role": by_role,
        "by_layer": by_layer,
        "by_status": by_status,
        "by_project": by_project,
        "metadata": topology.metadata,
    }
