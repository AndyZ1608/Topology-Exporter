"""Normalized inventory, summary, search, and refresh endpoints."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.services.sync_service import get_sync_service


router = APIRouter(tags=["inventory"])


@router.get("/cloud/summary")
async def cloud_summary(
    project_id: str | None = Query(None, description="Scope inventory to one project"),
):
    return get_sync_service().get_cloud_summary(project_id=project_id)


def _resource_or_404(resource_type: str, resource_id: str) -> dict:
    resource = get_sync_service().get_resource(resource_type, resource_id)
    if resource is None:
        raise HTTPException(
            status_code=404,
            detail=f"{resource_type.title()} {resource_id} not found",
        )
    return resource


@router.get("/servers/{server_id}")
async def server_detail(server_id: str):
    return _resource_or_404("server", server_id)


@router.get("/networks/{network_id}")
async def network_detail(network_id: str):
    return _resource_or_404("network", network_id)


@router.get("/routers/{router_id}")
async def router_detail(router_id: str):
    return _resource_or_404("router", router_id)


@router.get("/search")
async def search(q: str = Query(..., min_length=1, max_length=256)):
    results = get_sync_service().search(q)
    return {"query": q, "total": len(results), "results": results}


@router.post("/discovery/refresh")
async def refresh_discovery():
    status = await run_in_threadpool(get_sync_service().sync, True)
    return status.model_dump()
