"""API routes package."""
from fastapi import APIRouter

from .projects import router as projects_router
from .topology import router as topology_router
from .nodes import router as nodes_router
from .paths import router as paths_router
from .status import router as status_router
from .inventory import router as inventory_router

# Main API router
api_router = APIRouter(prefix="/api/v1")

api_router.include_router(projects_router)
api_router.include_router(topology_router)
api_router.include_router(nodes_router)
api_router.include_router(paths_router)
api_router.include_router(status_router)
api_router.include_router(inventory_router)

__all__ = ["api_router"]
