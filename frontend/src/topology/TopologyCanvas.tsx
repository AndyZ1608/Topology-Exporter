/**
 * Main topology canvas component.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  Panel,
  NodeChange,
  EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { nodeTypes } from './nodes/CustomNodes';
import { edgeTypes } from './edges/CustomEdges';
import { applyLayout, LAYOUT_DIRECTIONS, LayoutDirection } from './layout';
import type { TopologyNode, TopologyEdge, TopologyFilters } from '@/types';
import { getTopology, getInternetPath } from '@/api/topology';

interface TopologyCanvasProps {
  filters?: TopologyFilters;
  onNodeClick?: (node: TopologyNode | null) => void;
  onEdgeClick?: (edge: TopologyEdge | null) => void;
}

// Helper type cast
function castToTopologyNode(data: unknown): TopologyNode {
  return data as TopologyNode;
}

function castToTopologyEdge(edge: Edge): TopologyEdge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    relationship: (edge.data?.relationship as TopologyEdge['relationship']) || 'attached_to',
    inferred: Boolean(edge.data?.inferred),
    confidence: Number(edge.data?.confidence) || 1.0,
    properties: edge.data || {},
  };
}

const TopologyCanvas: React.FC<TopologyCanvasProps> = ({
  filters,
  onNodeClick,
  onEdgeClick,
}) => {
  const [nodes, setNodes] = useNodesState<Node>([]);
  const [edges, setEdges] = useEdgesState<Edge>([]);
  const [loading, setLoading] = useState(true);
  const [layoutDirection, setLayoutDirection] = useState<LayoutDirection>('TB');
  const [layouting, setLayouting] = useState(false);
  const [highlightedPath, setHighlightedPath] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Load topology data
  useEffect(() => {
    const loadTopology = async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await getTopology({
          projectIds: filters?.projectIds,
          resourceTypes: filters?.resourceTypes,
          status: filters?.status || undefined,
          search: filters?.search || undefined,
          view: filters?.view || 'traffic',
        });

        if (data.nodes && data.edges) {
          await applyTopologyLayout(data.nodes, data.edges);
        }
      } catch (err) {
        console.error('Failed to load topology:', err);
        setError('Failed to load topology data');
      } finally {
        setLoading(false);
      }
    };

    loadTopology();
  }, [filters]);

  // Apply layout to topology data
  const applyTopologyLayout = async (
    topologyNodes: TopologyNode[],
    topologyEdges: TopologyEdge[]
  ) => {
    setLayouting(true);

    try {
      const direction = LAYOUT_DIRECTIONS[layoutDirection].elk;
      const { nodes: layoutedNodes, edges: layoutedEdges } = await applyLayout(
        topologyNodes,
        topologyEdges,
        { direction }
      );

      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
    } catch (err) {
      console.error('Layout failed:', err);
    } finally {
      setLayouting(false);
    }
  };

  // Handle layout direction change
  const handleLayoutChange = useCallback(async (direction: LayoutDirection) => {
    setLayoutDirection(direction);

    if (nodes.length > 0) {
      setLayouting(true);
      try {
        // Re-derive topology data from nodes
        const topologyNodes: TopologyNode[] = nodes.map((n) => castToTopologyNode(n.data));
        const topologyEdges: TopologyEdge[] = edges.map((e) => castToTopologyEdge(e));

        const elkDirection = LAYOUT_DIRECTIONS[direction].elk;
        const { nodes: layoutedNodes, edges: layoutedEdges } = await applyLayout(
          topologyNodes,
          topologyEdges,
          { direction: elkDirection }
        );

        setNodes(layoutedNodes);
        setEdges(layoutedEdges);
      } catch (err) {
        console.error('Re-layout failed:', err);
      } finally {
        setLayouting(false);
      }
    }
  }, [nodes, edges, setNodes, setEdges]);

  // Handle node changes
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      setNodes((nds) => applyNodeChanges(changes, nds));
    },
    [setNodes]
  );

  // Handle edge changes
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      setEdges((eds) => applyEdgeChanges(changes, eds));
    },
    [setEdges]
  );

  // Handle node click
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const topologyNode = castToTopologyNode(node.data);
      onNodeClick?.(topologyNode);

      // If it's a server, fetch and highlight internet path
      if (topologyNode.resource_type === 'server') {
        highlightInternetPath(topologyNode.resource_id);
      }
    },
    [onNodeClick]
  );

  // Handle edge click
  const handleEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      const topologyEdge = castToTopologyEdge(edge);
      onEdgeClick?.(topologyEdge);
    },
    [onEdgeClick]
  );

  // Highlight internet path for a server
  const highlightInternetPath = async (serverId: string) => {
    try {
      const path = await getInternetPath(serverId);
      if (path.found) {
        setHighlightedPath(path.path);
      } else {
        setHighlightedPath([]);
      }
    } catch (err) {
      console.error('Failed to get internet path:', err);
      setHighlightedPath([]);
    }
  };

  // Apply path highlighting
  const styledEdges = useMemo(() => {
    return edges.map((edge) => {
      const isInPath = highlightedPath.includes(edge.source) && highlightedPath.includes(edge.target);
      const isSource = highlightedPath.includes(edge.source);
      const isTarget = highlightedPath.includes(edge.target);

      if (isInPath) {
        return {
          ...edge,
          style: {
            ...edge.style,
            stroke: '#3b82f6',
            strokeWidth: 3,
          },
          animated: true,
        };
      }

      if (isSource || isTarget) {
        return {
          ...edge,
          style: {
            ...edge.style,
            opacity: 0.5,
          },
        };
      }

      return {
        ...edge,
        style: {
          ...edge.style,
          opacity: highlightedPath.length > 0 ? 0.2 : 1,
        },
      };
    });
  }, [edges, highlightedPath]);

  // Clear path highlight on background click
  const handlePaneClick = useCallback(() => {
    setHighlightedPath([]);
    onNodeClick?.(null);
  }, [onNodeClick]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading topology...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center text-red-600">
          <p className="text-lg font-medium">Error</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={styledEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        onPaneClick={handlePaneClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        defaultEdgeOptions={{
          type: 'confirmed',
        }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e5e7eb" />
        <Controls className="bg-white border border-gray-200 rounded-lg shadow-sm" />
        <MiniMap
          className="bg-white border border-gray-200 rounded-lg shadow-sm"
          nodeColor={(node) => {
            const role = castToTopologyNode(node.data)?.role;
            switch (role) {
              case 'vm':
                return '#3b82f6';
              case 'firewall':
                return '#ef4444';
              case 'router':
                return '#a855f7';
              case 'network':
                return '#22c55e';
              case 'internet':
                return '#06b6d4';
              default:
                return '#6b7280';
            }
          }}
          maskColor="rgba(243, 244, 246, 0.8)"
        />

        {/* Layout Direction Panel */}
        <Panel position="top-left" className="bg-white border border-gray-200 rounded-lg shadow-sm p-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-600">Layout:</span>
            <select
              value={layoutDirection}
              onChange={(e) => handleLayoutChange(e.target.value as LayoutDirection)}
              className="text-xs border border-gray-200 rounded px-2 py-1"
              disabled={layouting}
            >
              {Object.entries(LAYOUT_DIRECTIONS).map(([key, { label }]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        </Panel>

        {/* Legend Panel */}
        <Panel position="bottom-left" className="bg-white border border-gray-200 rounded-lg shadow-sm p-3 text-xs">
          <div className="font-medium text-gray-700 mb-2">Legend</div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 bg-gray-600"></div>
              <span>Confirmed relationship</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 border-t border-dashed border-gray-400"></div>
              <span>Inferred relationship</span>
            </div>
          </div>
          {highlightedPath.length > 0 && (
            <div className="mt-2 pt-2 border-t border-gray-200">
              <div className="text-primary-600">Internet path highlighted</div>
              <button
                onClick={() => setHighlightedPath([])}
                className="text-xs text-gray-500 hover:text-gray-700 mt-1"
              >
                Clear highlight
              </button>
            </div>
          )}
        </Panel>

        {/* Stats Panel */}
        <Panel position="top-right" className="bg-white border border-gray-200 rounded-lg shadow-sm p-3 text-xs">
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-500">Nodes:</span>
              <span className="font-medium">{nodes.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Edges:</span>
              <span className="font-medium">{edges.length}</span>
            </div>
          </div>
          {layouting && (
            <div className="mt-2 pt-2 border-t border-gray-200 text-gray-500">
              Calculating layout...
            </div>
          )}
        </Panel>
      </ReactFlow>
    </div>
  );
};

export default TopologyCanvas;
