"""
Nodes API endpoints.
"""
from fastapi import APIRouter, HTTPException
from app.services.sync_service import get_sync_service

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("/{node_id}")
async def get_node(node_id: str):
    """
    Get detailed information about a specific node.
    """
    sync_service = get_sync_service()

    if not sync_service.current_topology:
        raise HTTPException(status_code=404, detail="No topology available")

    # Find the node
    for node in sync_service.current_topology.nodes:
        if node.id == node_id:
            # Get connected nodes
            connected = []
            for edge in sync_service.current_topology.edges:
                if edge.source == node_id:
                    connected.append({"node_id": edge.target, "relationship": edge.relationship})
                elif edge.target == node_id:
                    connected.append({"node_id": edge.source, "relationship": edge.relationship})

            # Build detail response
            detail = node.model_dump()
            detail["connected_nodes"] = connected

            return detail

    raise HTTPException(status_code=404, detail=f"Node {node_id} not found")


@router.get("/{node_id}/connections")
async def get_node_connections(node_id: str):
    """
    Get all connections for a specific node.
    """
    sync_service = get_sync_service()

    if not sync_service.current_topology:
        raise HTTPException(status_code=404, detail="No topology available")

    # Find the node
    node = None
    for n in sync_service.current_topology.nodes:
        if n.id == node_id:
            node = n
            break

    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    # Get connections
    inbound = []
    outbound = []

    for edge in sync_service.current_topology.edges:
        if edge.source == node_id:
            outbound.append({
                "target": edge.target,
                "relationship": edge.relationship,
                "inferred": edge.inferred,
                "confidence": edge.confidence,
                "properties": edge.properties.model_dump(),
            })
        elif edge.target == node_id:
            inbound.append({
                "source": edge.source,
                "relationship": edge.relationship,
                "inferred": edge.inferred,
                "confidence": edge.confidence,
                "properties": edge.properties.model_dump(),
            })

    return {
        "node_id": node_id,
        "node_name": node.name,
        "inbound": inbound,
        "outbound": outbound,
    }


@router.get("/{node_id}/ports")
async def get_node_ports(node_id: str):
    """
    Get ports associated with a node (for servers).
    """
    sync_service = get_sync_service()

    if not sync_service.current_topology:
        raise HTTPException(status_code=404, detail="No topology available")

    # Find the node
    node = None
    for n in sync_service.current_topology.nodes:
        if n.id == node_id:
            node = n
            break

    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    # Only servers have ports in our model
    if node.resource_type != "server":
        return {"node_id": node_id, "ports": []}

    # Get port information from edges
    ports = []
    for edge in sync_service.current_topology.edges:
        if edge.source == node_id and edge.relationship == "attached_to":
            # This is a port connection
            ports.append({
                "port_id": edge.properties.port_id,
                "network_id": edge.target.replace("network:", ""),
                "ip_addresses": node.properties.ips,
                "mac_addresses": node.properties.mac_addresses,
            })

    return {
        "node_id": node_id,
        "node_name": node.name,
        "ports": ports,
    }
