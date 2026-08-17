/**
 * Topology types matching the backend schemas.
 */

export interface NodeProperties {
  ips: string[];
  mac_addresses: string[];
  cidr?: string;
  gateway_ip?: string;
  provider_network_type?: string;
  provider_physical_network?: string;
  provider_segmentation_id?: number;
  is_external: boolean;
  is_shared: boolean;
  ha_members: string[];
  interfaces: Record<string, string>;
  vm_count: number;
  flavor?: string;
  metadata: Record<string, string>;
  external_gateway?: {
    network_id: string;
    enable_snat?: boolean;
  };
  floating_ips: string[];
  security_groups: string[];
}

export interface TopologyNode {
  id: string;
  resource_id: string;
  resource_type: 'server' | 'network' | 'subnet' | 'router' | 'floatingip' | 'trunk' | 'ha_group' | 'internet';
  role: 'vm' | 'firewall' | 'load_balancer' | 'router' | 'network' | 'subnet' | 'internet' | 'ha_group' | 'unknown';
  name: string;
  project_id?: string;
  project_name?: string;
  status: string;
  layer: 'workload' | 'network' | 'gateway' | 'external' | 'internet';
  properties: NodeProperties;
  tags: string[];
  aggregated: boolean;
  aggregated_count: number;
  parent_id?: string;
}

export interface EdgeProperties {
  vlan_id?: number;
  segmentation_type?: string;
  floating_ip?: string;
  fixed_ip?: string;
  port_id?: string;
  subnet_id?: string;
  trunk_id?: string;
}

export interface TopologyEdge {
  id: string;
  source: string;
  target: string;
  relationship: 'attached_to' | 'contains' | 'router_interface' | 'external_gateway' | 'floating_ip' | 'trunk_parent' | 'trunk_subport' | 'egress_via' | 'ha_member' | 'internet_uplink';
  inferred: boolean;
  confidence: number;
  properties: EdgeProperties;
}

export interface TopologyResponse {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  metadata?: Record<string, unknown>;
  timestamp?: string;
}

export interface InternetPathResponse {
  source: string;
  destination: string;
  found: boolean;
  reason?: string;
  confidence: number;
  path: string[];
  inferred: boolean;
  path_nodes: TopologyNode[];
}

export interface SyncStatus {
  status: 'idle' | 'syncing' | 'success' | 'partial' | 'failed';
  last_sync?: string;
  last_duration?: number;
  last_error?: string;
  partial: boolean;
  failed_collectors: string[];
  node_count: number;
  edge_count: number;
}

export interface Project {
  id: string;
  name: string;
}

export interface ProjectsResponse {
  projects: Project[];
  total: number;
}

// Filter types
export interface TopologyFilters {
  projectIds: string[];
  resourceTypes: string[];
  status: string;
  search: string;
  view: 'traffic' | 'infrastructure' | 'project';
}

// View modes
export type ViewMode = 'traffic' | 'infrastructure' | 'project';

// Node roles for display
export const NODE_ROLE_LABELS: Record<string, string> = {
  vm: 'VM',
  firewall: 'Firewall',
  router: 'Router',
  network: 'Network',
  subnet: 'Subnet',
  load_balancer: 'Load Balancer',
  ha_group: 'HA Group',
  internet: 'Internet',
  unknown: 'Unknown',
};

// Resource type to role mapping
export const RESOURCE_TYPE_TO_ROLE: Record<string, string> = {
  server: 'vm',
  network: 'network',
  subnet: 'subnet',
  router: 'router',
  floatingip: 'floatingip',
  trunk: 'trunk',
  ha_group: 'ha_group',
  internet: 'internet',
};
