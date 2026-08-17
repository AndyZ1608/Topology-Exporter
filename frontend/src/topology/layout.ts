/**
 * Topology layout utilities using ELK.js for hierarchical layout.
 */
import ELK from 'elkjs/lib/elk.bundled.js';
import type { Node, Edge } from '@xyflow/react';
import type { TopologyNode, TopologyEdge } from '@/types';

// ELK.js initialization options
const elk = new ELK();

export interface ELKLayoutOptions {
  direction: 'DOWN' | 'UP' | 'RIGHT' | 'LEFT';
  spacing: number;
  nodeWidth: number;
  nodeHeight: number;
}

const defaultOptions: ELKLayoutOptions = {
  direction: 'DOWN',
  spacing: 50,
  nodeWidth: 200,
  nodeHeight: 100,
};

interface ELKNode {
  id: string;
  width?: number;
  height?: number;
  x?: number;
  y?: number;
  properties?: {
    layer?: string;
    role?: string;
  };
}

interface ELKEdge {
  id: string;
  sources?: string[];
  targets?: string[];
  properties?: {
    inferred?: boolean;
  };
}

interface ELKGraph {
  id?: string;
  children?: ELKNode[];
  edges?: ELKEdge[];
  layoutOptions?: Record<string, string | number>;
}

/**
 * Convert topology data to ELK format
 */
function toELKFormat(
  nodes: TopologyNode[],
  _edges: TopologyEdge[]
): { nodes: ELKNode[]; edges: ELKEdge[] } {
  const elkNodes: ELKNode[] = nodes.map((node) => ({
    id: node.id,
    width: defaultOptions.nodeWidth,
    height: defaultOptions.nodeHeight,
    properties: {
      layer: node.layer,
      role: node.role,
    },
  }));

  const elkEdges: ELKEdge[] = [];

  return { nodes: elkNodes, edges: elkEdges };
}

/**
 * Apply hierarchical layout using ELK.js
 */
export async function applyLayout(
  topologyNodes: TopologyNode[],
  topologyEdges: TopologyEdge[],
  options: Partial<ELKLayoutOptions> = {}
): Promise<{ nodes: Node[]; edges: Edge[] }> {
  const opts = { ...defaultOptions, ...options };

  const { nodes: elkNodes, edges: elkEdges } = toELKFormat(topologyNodes, topologyEdges);

  // Add edges to ELK format
  elkEdges.push(
    ...topologyEdges.map((edge) => ({
      id: edge.id,
      sources: [edge.source],
      targets: [edge.target],
      properties: {
        inferred: edge.inferred,
      },
    }))
  );

  // Define layer-based grouping for ELK using string type for layoutOptions
  const layoutOptions: Record<string, string> = {
    'elk.algorithm': 'layered',
    'elk.layered.spacing.nodeNodeBetweenLayers': String(opts.spacing),
    'elk.layered.spacing.edgeNodeBetweenLayers': String(opts.spacing / 2),
    'elk.direction': opts.direction,
    'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
    'elk.spacing.nodeNode': String(opts.spacing),
    'elk.padding': '[top=50,left=50,bottom=50,right=50]',
  };

  try {
    const layoutedGraph: ELKGraph = await elk.layout({
      id: 'root',
      layoutOptions,
      children: elkNodes,
      edges: elkEdges,
    });

    // Convert back to React Flow format
    const flowNodes: Node[] = (layoutedGraph.children || []).map((elkNode) => {
      const originalNode = topologyNodes.find((n) => n.id === elkNode.id);
      return {
        id: elkNode.id,
        type: getNodeType(originalNode?.role || 'vm'),
        position: {
          x: elkNode.x || 0,
          y: elkNode.y || 0,
        },
        data: {
          ...originalNode,
          width: elkNode.width || opts.nodeWidth,
          height: elkNode.height || opts.nodeHeight,
        },
      };
    });

    const flowEdges: Edge[] = (layoutedGraph.edges || []).map((elkEdge) => {
      const originalEdge = topologyEdges.find((e) => e.id === elkEdge.id);
      return {
        id: elkEdge.id,
        source: elkEdge.sources?.[0] || '',
        target: elkEdge.targets?.[0] || '',
        type: originalEdge?.inferred ? 'inferred' : 'confirmed',
        animated: originalEdge?.inferred || false,
        style: {
          strokeDasharray: originalEdge?.inferred ? '5,5' : undefined,
          stroke: originalEdge?.inferred ? '#9ca3af' : '#374151',
        },
        data: {
          relationship: originalEdge?.relationship,
          confidence: originalEdge?.confidence,
          inferred: originalEdge?.inferred,
        },
      };
    });

    return { nodes: flowNodes, edges: flowEdges };
  } catch (error) {
    console.error('Layout error:', error);
    // Fallback to simple grid layout
    return fallbackLayout(topologyNodes, topologyEdges);
  }
}

/**
 * Fallback grid layout when ELK fails
 */
function fallbackLayout(
  nodes: TopologyNode[],
  edges: TopologyEdge[]
): { nodes: Node[]; edges: Edge[] } {
  // Group by layer
  const layers: Record<string, TopologyNode[]> = {};
  for (const node of nodes) {
    const layer = node.layer;
    if (!layers[layer]) layers[layer] = [];
    layers[layer].push(node);
  }

  // Layer order
  const layerOrder = ['workload', 'network', 'gateway', 'external', 'internet'];
  const sortedLayers = layerOrder.filter((l) => layers[l]);

  // Assign positions
  const flowNodes: Node[] = [];
  const spacingX = 250;
  const spacingY = 150;
  const startY = 50;

  for (let layerIdx = 0; layerIdx < sortedLayers.length; layerIdx++) {
    const layer = sortedLayers[layerIdx];
    const layerNodes = layers[layer];
    const y = startY + layerIdx * spacingY;

    for (let nodeIdx = 0; nodeIdx < layerNodes.length; nodeIdx++) {
      const node = layerNodes[nodeIdx];
      const x = 100 + nodeIdx * spacingX - (layerNodes.length * spacingX) / 2;

      flowNodes.push({
        id: node.id,
        type: getNodeType(node.role),
        position: { x, y },
        data: { ...node },
      });
    }
  }

  // Convert edges
  const flowEdges: Edge[] = edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: edge.inferred ? 'inferred' : 'confirmed',
    animated: edge.inferred,
    style: {
      strokeDasharray: edge.inferred ? '5,5' : undefined,
      stroke: edge.inferred ? '#9ca3af' : '#374151',
    },
  }));

  return { nodes: flowNodes, edges: flowEdges };
}

/**
 * Get React Flow node type from role
 */
function getNodeType(role: string): string {
  const typeMap: Record<string, string> = {
    vm: 'server',
    server: 'server',
    firewall: 'firewall',
    router: 'router',
    network: 'network',
    subnet: 'subnet',
    load_balancer: 'loadbalancer',
    ha_group: 'hagroup',
    internet: 'internet',
  };
  return typeMap[role] || 'default';
}

/**
 * Direction options for layout
 */
export const LAYOUT_DIRECTIONS = {
  'TB': { label: 'Top to Bottom', elk: 'DOWN' as const },
  'BT': { label: 'Bottom to Top', elk: 'UP' as const },
  'LR': { label: 'Left to Right', elk: 'RIGHT' as const },
  'RL': { label: 'Right to Left', elk: 'LEFT' as const },
};

export type LayoutDirection = keyof typeof LAYOUT_DIRECTIONS;
