"""
Paths API endpoints - internet path discovery.
"""
from fastapi import APIRouter, HTTPException

from app.services.sync_service import get_sync_service

router = APIRouter(prefix="/path", tags=["paths"])


@router.get("/{server_id}/internet")
async def get_internet_path(server_id: str):
    """
    Find the logical path from a server to the Internet.

    This is an inference-based analysis, not verified packet routing.

    Returns:
        - found: Whether a path was found
        - path: List of node IDs from server to internet
        - path_nodes: Full node objects for the path
        - confidence: Confidence score based on inferred relationships
        - inferred: Whether any relationships in the path were inferred
        - reason: If not found, explains why
    """
    sync_service = get_sync_service()

    if not sync_service.current_topology:
        raise HTTPException(status_code=404, detail="No topology available")

    # Verify the server exists
    server_node_id = f"server:{server_id}"
    found = False
    for node in sync_service.current_topology.nodes:
        if node.id == server_node_id:
            found = True
            break

    if not found:
        # Try just the server_id
        for node in sync_service.current_topology.nodes:
            if node.resource_id == server_id:
                # Found it, but we need to use the node's id
                result = sync_service.find_internet_path(node.resource_id)
                return result

        raise HTTPException(status_code=404, detail=f"Server {server_id} not found")

    # Find the path
    result = sync_service.find_internet_path(server_id)
    return result


@router.get("/{server_id}/paths")
async def get_all_paths(server_id: str):
    """
    Get all possible paths from a server (not just to Internet).
    """
    sync_service = get_sync_service()

    if not sync_service.current_topology:
        raise HTTPException(status_code=404, detail="No topology available")

    # Find all paths starting from this server
    server_node_id = f"server:{server_id}"
    paths = []

    # Build adjacency
    downstream: dict = {}
    for edge in sync_service.current_topology.edges:
        if edge.source not in downstream:
            downstream[edge.source] = []
        downstream[edge.source].append({
            "target": edge.target,
            "relationship": edge.relationship,
            "inferred": edge.inferred,
            "confidence": edge.confidence,
        })

    # Simple BFS to find all reachable nodes
    visited = {server_node_id}
    queue = [server_node_id]

    while queue:
        current = queue.pop(0)
        for conn in downstream.get(current, []):
            target = conn["target"]
            if target not in visited:
                visited.add(target)
                queue.append(target)
                paths.append({
                    "source": current,
                    "target": target,
                    "relationship": conn["relationship"],
                    "inferred": conn["inferred"],
                    "confidence": conn["confidence"],
                })

    return {
        "server_id": server_id,
        "reachable_nodes": list(visited),
        "paths": paths,
    }
