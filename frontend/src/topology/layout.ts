/** Build the single operational Traffic Topology and lay it out with ELK. */
import ELK from 'elkjs/lib/elk.bundled.js';
import { MarkerType, type Edge, type Node } from '@xyflow/react';
import type { NodeProperties, TopologyEdge, TopologyNode } from '@/types';

const elk = new ELK();
const VM_WIDTH = 150;
const VM_HEIGHT = 58;
const GROUP_HEADER = 72;
const GROUP_PADDING = 18;
const GRID_GAP = 14;
const DEVICE_WIDTH = 170;
const DEVICE_HEIGHT = 66;
const ROUTER_HEIGHT = 82;

interface GroupSpec {
  node: TopologyNode;
  children: TopologyNode[];
  width: number;
  height: number;
  columns: number;
}

interface ELKNode {
  id: string;
  width: number;
  height: number;
  x?: number;
  y?: number;
}

function emptyProperties(): NodeProperties {
  return {
    ips: [], mac_addresses: [], is_external: false, is_shared: false,
    ha_members: [], interfaces: {}, vm_count: 0,
    metadata: { synthetic: true }, floating_ips: [], security_groups: [], subnets: [],
    router_interfaces: [],
  };
}

function unconnectedGroup(): TopologyNode {
  return {
    id: 'group:unconnected', resource_id: 'unconnected', resource_type: 'network',
    role: 'network', name: 'Unconnected / Unknown', status: 'UNKNOWN', layer: 'network',
    properties: emptyProperties(), tags: [], aggregated: false, aggregated_count: 0,
  };
}

function groupDimensions(vmCount: number): Pick<GroupSpec, 'width' | 'height' | 'columns'> {
  if (vmCount === 0) return { width: 230, height: 98, columns: 1 };
  const columns = Math.min(5, Math.max(1, Math.ceil(Math.sqrt(vmCount))));
  const rows = Math.ceil(vmCount / columns);
  return {
    columns,
    width: GROUP_PADDING * 2 + columns * VM_WIDTH + (columns - 1) * GRID_GAP,
    height: GROUP_HEADER + GROUP_PADDING + rows * VM_HEIGHT + (rows - 1) * GRID_GAP,
  };
}

function displayNodeType(node: TopologyNode): string {
  if (node.resource_type === 'network') return 'networkGroup';
  if (node.resource_type === 'server') {
    if (node.role === 'firewall') return 'firewall';
    if (node.role === 'router') return 'appliance';
    return 'server';
  }
  if (node.resource_type === 'router') return 'router';
  if (node.resource_type === 'internet') return 'internet';
  return 'default';
}

export async function applyLayout(
  topologyNodes: TopologyNode[],
  topologyEdges: TopologyEdge[],
): Promise<{ nodes: Node[]; edges: Edge[] }> {
  const operationalNodes = topologyNodes.filter((node) =>
    ['server', 'network', 'router', 'internet'].includes(node.resource_type),
  );
  const nodeById = new Map(operationalNodes.map((node) => [node.id, node]));
  const servers = operationalNodes.filter((node) => node.resource_type === 'server');
  const networks = operationalNodes.filter(
    (node) => node.resource_type === 'network' && !node.properties.is_external,
  );
  const visibleOperationalNodes = operationalNodes.filter(
    (node) => node.resource_type !== 'network' || !node.properties.is_external,
  );
  const visibleNodeIds = new Set(visibleOperationalNodes.map((node) => node.id));
  const attachedNetworks = new Map<string, Set<string>>();

  for (const edge of topologyEdges) {
    if (edge.relationship !== 'attached_to') continue;
    if (!nodeById.has(edge.source) || !nodeById.has(edge.target)) continue;
    const serverId = nodeById.get(edge.source)?.resource_type === 'server' ? edge.source : edge.target;
    const networkId = serverId === edge.source ? edge.target : edge.source;
    if (nodeById.get(networkId)?.resource_type !== 'network') continue;
    if (!attachedNetworks.has(serverId)) attachedNetworks.set(serverId, new Set());
    attachedNetworks.get(serverId)?.add(networkId);
  }

  const childrenByGroup = new Map<string, TopologyNode[]>();
  const parentByServer = new Map<string, string>();
  for (const server of servers) {
    const memberships = [...(attachedNetworks.get(server.id) || [])];
    const internalMemberships = memberships.filter(
      (networkId) => !nodeById.get(networkId)?.properties.is_external,
    );
    const parentId = memberships.length === 0
      ? 'group:unconnected'
      : memberships.length === 1 && internalMemberships.length === 1
        ? internalMemberships[0]
        : undefined;
    if (!parentId) continue;
    parentByServer.set(server.id, parentId);
    const children = childrenByGroup.get(parentId) || [];
    children.push(server);
    childrenByGroup.set(parentId, children);
  }

  const groupNodes = [...networks];
  if (childrenByGroup.has('group:unconnected')) groupNodes.push(unconnectedGroup());
  const groupSpecs = new Map<string, GroupSpec>();
  for (const network of groupNodes.sort((a, b) => a.name.localeCompare(b.name))) {
    const children = (childrenByGroup.get(network.id) || []).sort((a, b) => a.name.localeCompare(b.name));
    groupSpecs.set(network.id, { node: network, children, ...groupDimensions(children.length) });
  }

  const standaloneNodes = visibleOperationalNodes.filter(
    (node) => node.resource_type !== 'network' && !parentByServer.has(node.id),
  );
  const elkNodes: ELKNode[] = [
    ...[...groupSpecs.values()].map((group) => ({ id: group.node.id, width: group.width, height: group.height })),
    ...standaloneNodes.map((node) => ({
      id: node.id,
      width: node.resource_type === 'server' ? VM_WIDTH : DEVICE_WIDTH,
      height: node.resource_type === 'server'
        ? VM_HEIGHT
        : node.resource_type === 'router' ? ROUTER_HEIGHT : DEVICE_HEIGHT,
    })),
  ];
  const topLevelIds = new Set(elkNodes.map((node) => node.id));

  const visibleEdges = topologyEdges.filter((edge) => {
    if (!visibleNodeIds.has(edge.source) || !visibleNodeIds.has(edge.target)) return false;
    if (['contains', 'ha_member', 'trunk_parent', 'trunk_subport', 'egress_via'].includes(edge.relationship)) return false;
    return !(edge.relationship === 'attached_to' && parentByServer.get(edge.source) === edge.target);
  });

  const elkEdges = visibleEdges.flatMap((edge) => {
    if (!topLevelIds.has(edge.source) || !topLevelIds.has(edge.target)) return [];
    let source = edge.source;
    let target = edge.target;
    if (edge.relationship === 'attached_to') {
      const server = nodeById.get(edge.source);
      const network = nodeById.get(edge.target);
      const portRole = edge.properties.port_id
        ? server?.properties.interfaces?.[edge.properties.port_id]?.role
        : undefined;
      const isAppliance = server?.role === 'firewall' || server?.role === 'router';
      if (isAppliance && !network?.properties.is_external && portRole !== 'WAN') {
        source = edge.target;
        target = edge.source;
      }
    }
    return [{ id: edge.id, sources: [source], targets: [target] }];
  });

  const graph = await elk.layout({
    id: 'traffic-topology',
    layoutOptions: {
      'elk.algorithm': 'layered', 'elk.direction': 'RIGHT', 'elk.edgeRouting': 'ORTHOGONAL',
      'elk.spacing.nodeNode': '56', 'elk.layered.spacing.nodeNodeBetweenLayers': '100',
      'elk.layered.spacing.edgeNodeBetweenLayers': '32',
      'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
      'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
      'elk.layered.considerModelOrder.strategy': 'NODES_AND_EDGES',
      'elk.padding': '[top=50,left=50,bottom=50,right=50]',
    },
    children: elkNodes,
    edges: elkEdges,
  });
  const positions = new Map((graph.children || []).map((node) => [node.id, node]));
  const flowNodes: Node[] = [];

  for (const group of groupSpecs.values()) {
    const position = positions.get(group.node.id);
    flowNodes.push({
      id: group.node.id, type: 'networkGroup',
      position: { x: position?.x || 0, y: position?.y || 0 }, data: { ...group.node },
      style: { width: group.width, height: group.height }, zIndex: 0,
    });
    group.children.forEach((server, index) => {
      const column = index % group.columns;
      const row = Math.floor(index / group.columns);
      flowNodes.push({
        id: server.id, type: displayNodeType(server), parentId: group.node.id, extent: 'parent',
        position: {
          x: GROUP_PADDING + column * (VM_WIDTH + GRID_GAP),
          y: GROUP_HEADER + row * (VM_HEIGHT + GRID_GAP),
        },
        data: { ...server }, style: { width: VM_WIDTH, height: VM_HEIGHT }, zIndex: 2,
      });
    });
  }

  for (const node of standaloneNodes) {
    const position = positions.get(node.id);
    flowNodes.push({
      id: node.id, type: displayNodeType(node),
      position: { x: position?.x || 0, y: position?.y || 0 }, data: { ...node },
      style: {
        width: node.resource_type === 'server' ? VM_WIDTH : DEVICE_WIDTH,
        height: node.resource_type === 'server'
          ? VM_HEIGHT
          : node.resource_type === 'router' ? ROUTER_HEIGHT : DEVICE_HEIGHT,
      },
      zIndex: 2,
    });
  }

  const flowEdges: Edge[] = visibleEdges.map((edge) => ({
    id: edge.id, source: edge.source, target: edge.target,
    type: edge.inferred ? 'inferred' : 'confirmed', animated: false,
    data: {
      relationship: edge.relationship,
      confidence: edge.confidence,
      ...edge.properties,
      label: edge.relationship === 'router_interface' && edge.properties.gateway_ip
        ? `GW ${edge.properties.gateway_ip}`
        : edge.target === 'internet' && edge.properties.ip_address
          ? `WAN ${edge.properties.ip_address}`
          : undefined,
    },
    style: { stroke: edge.inferred ? '#94a3b8' : '#64748b' },
    markerEnd: ['router_interface', 'external_gateway', 'internet_uplink'].includes(edge.relationship)
      ? { type: MarkerType.ArrowClosed, width: 12, height: 12, color: '#64748b' }
      : undefined,
  }));
  return { nodes: flowNodes, edges: flowEdges };
}
