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
  interfaces: Record<string, {
    role?: string;
    network_id?: string;
    network_name?: string;
    is_external?: boolean;
    mac_address?: string;
    ip_addresses?: string[];
    subnet_ids?: string[];
    security_groups?: string[];
    subnets?: Array<{ id: string; name?: string; cidr?: string }>;
  }>;
  vm_count: number;
  flavor?: string;
  metadata: Record<string, string | number | boolean | null>;
  external_gateway?: {
    network_id: string;
    network_name?: string;
    enable_snat?: boolean;
    subnet_id?: string;
    subnet_name?: string;
    subnet_cidr?: string;
    ip_address?: string;
    fixed_ips?: Array<{
      subnet_id?: string;
      subnet_name?: string;
      subnet_cidr?: string;
      ip_address?: string;
    }>;
  };
  floating_ips: string[];
  security_groups: string[];
  subnets: Array<{
    id: string;
    name?: string;
    cidr?: string;
    gateway_ip?: string;
  }>;
  router_interfaces: Array<{
    port_id?: string;
    network_id?: string;
    network_name?: string;
    subnet_id?: string;
    subnet_name?: string;
    subnet_cidr?: string;
    ip_address?: string;
  }>;
}

export interface TopologyNode {
  id: string;
  resource_id: string;
  resource_type: 'server' | 'network' | 'subnet' | 'router' | 'floatingip' | 'trunk' | 'firewall' | 'firewall_member' | 'internet';
  role: 'vm' | 'firewall' | 'load_balancer' | 'router' | 'network' | 'subnet' | 'internet' | 'unknown';
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
  network_id?: string;
  subnet_id?: string;
  mac_address?: string;
  trunk_id?: string;
  gateway_ip?: string;
  ip_address?: string;
  external_network_id?: string;
  external_network_name?: string;
  external_subnet_id?: string;
  external_subnet_cidr?: string;
  connection_kind?: 'router_external_gateway' | 'vm_external_interface';
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
  domain_id?: string;
}

export interface ProjectsResponse {
  projects: Project[];
  total: number;
}

export interface CloudSummary {
  projects: number;
  servers: number;
  networks: number;
  subnets: number;
  routers: number;
  floating_ips: number;
  last_sync?: string;
  sync_status: string;
  partial: boolean;
}

// Filter types
export interface TopologyFilters {
  projectIds: string[];
  resourceTypes: string[];
  status: string;
  search: string;
}

// Node roles for display
export const NODE_ROLE_LABELS: Record<string, string> = {
  vm: 'VM',
  firewall: 'Firewall',
  router: 'Router',
  network: 'Network',
  subnet: 'Subnet',
  load_balancer: 'Load Balancer',
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
  internet: 'internet',
};
