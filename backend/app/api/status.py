"""
Sync status API endpoints.
"""
from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.services.sync_service import get_sync_service

router = APIRouter(tags=["sync"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns basic application health status.
    """
    sync_status = get_sync_service().sync_status
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "demo_mode": settings.DEMO_MODE,
        "sync_status": sync_status.status,
        "last_sync": sync_status.last_sync.isoformat() if sync_status.last_sync else None,
    }


@router.get("/sync/status")
async def get_sync_status():
    """
    Get the current synchronization status.

    Returns:
    - status: idle, syncing, success, partial, failed
    - last_sync: Timestamp of last successful sync
    - last_duration: How long the last sync took
    - last_error: Error message if last sync failed
    - partial: Whether the last sync was partial
    - failed_collectors: List of failed OpenStack services
    - node_count: Number of nodes in current topology
    - edge_count: Number of edges in current topology
    """
    sync_service = get_sync_service()
    return sync_service.sync_status.model_dump()


@router.post("/sync/refresh")
async def trigger_sync():
    """
    Trigger an immediate topology refresh.

    This will start a new synchronization with OpenStack.
    """
    sync_service = get_sync_service()
    status = await run_in_threadpool(sync_service.sync, True)
    return status.model_dump()
