"""
Normalized topology schemas for API responses.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NodeProperties(BaseModel):
    """Additional properties for a node."""
    ips: list[str] = Field(default_factory=list)
    mac_addresses: list[str] = Field(default_factory=list)
    cidr: Optional[str] = None
    gateway_ip: Optional[str] = None
    provider_network_type: Optional[str] = None
    provider_physical_network: Optional[str] = None
    provider_segmentation_id: Optional[int] = None
    is_external: bool = False
    is_shared: bool = False
    ha_members: list[str] = Field(default_factory=list)
    interfaces: dict[str, str] = Field(default_factory=dict)
    vm_count: int = 0
    flavor: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    external_gateway: Optional[dict] = None
    floating_ips: list[str] = Field(default_factory=list)
    security_groups: list[str] = Field(default_factory=list)


class TopologyNode(BaseModel):
    """Normalized topology node."""
    id: str = Field(..., description="Unique identifier: {resource_type}:{resource_id}")
    resource_id: str = Field(..., description="OpenStack resource UUID")
    resource_type: str = Field(..., description="server, network, subnet, router, etc.")
    role: str = Field(..., description="Logical role: vm, firewall, router, network, internet, etc.")
    name: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    status: str = "UNKNOWN"
    layer: str = Field(..., description="workload, network, gateway, external, internet")
    properties: NodeProperties = Field(default_factory=NodeProperties)
    tags: list[str] = Field(default_factory=list)
    aggregated: bool = False
    aggregated_count: int = 0
    parent_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "server:550e8400-e29b-41d4-a716-446655440000",
                "resource_id": "550e8400-e29b-41d4-a716-446655440000",
                "resource_type": "server",
                "role": "vm",
                "name": "monitor01",
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "project_name": "NOC",
                "status": "ACTIVE",
                "layer": "workload",
                "properties": {
                    "ips": ["10.0.30.15"],
                    "mac_addresses": ["fa:16:3e:1a:b2:c3"],
                    "flavor": "m1.medium"
                }
            }
        }


class EdgeProperties(BaseModel):
    """Additional properties for an edge."""
    vlan_id: Optional[int] = None
    segmentation_type: Optional[str] = None
    floating_ip: Optional[str] = None
    fixed_ip: Optional[str] = None
    port_id: Optional[str] = None
    subnet_id: Optional[str] = None
    trunk_id: Optional[str] = None


class TopologyEdge(BaseModel):
    """Normalized topology edge."""
    id: str
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relationship: str = Field(..., description="attached_to, router_interface, external_gateway, etc.")
    inferred: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: EdgeProperties = Field(default_factory=EdgeProperties)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "edge-550e8400-e29b-41d4-a716-446655440001",
                "source": "server:550e8400-e29b-41d4-a716-446655440000",
                "target": "network:660e8400-e29b-41d4-a716-446655440000",
                "relationship": "attached_to",
                "inferred": False,
                "confidence": 1.0
            }
        }


class TopologyResponse(BaseModel):
    """Full topology response."""
    nodes: list[TopologyNode]
    edges: list[TopologyEdge]
    metadata: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class InternetPathResponse(BaseModel):
    """Internet path response for a server."""
    source: str
    destination: str = "internet"
    found: bool
    reason: Optional[str] = None
    confidence: float = 0.0
    path: list[str] = Field(default_factory=list)
    inferred: bool = False
    path_nodes: list[TopologyNode] = Field(default_factory=list)


class SyncStatusResponse(BaseModel):
    """Sync status response."""
    status: str = Field(..., description="idle, syncing, success, partial, failed")
    last_sync: Optional[datetime] = None
    last_duration: Optional[float] = None
    last_error: Optional[str] = None
    partial: bool = False
    failed_collectors: list[str] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0


class NodeDetailResponse(TopologyNode):
    """Detailed node information."""
    ports: list[dict] = Field(default_factory=list)
    connected_nodes: list[str] = Field(default_factory=list)
    inbound_paths: list[dict] = Field(default_factory=list)
    outbound_paths: list[dict] = Field(default_factory=list)
