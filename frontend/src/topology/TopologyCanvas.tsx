/** Single operational Traffic Topology canvas. */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ReactFlow, Background, Controls, MiniMap, BackgroundVariant,
  applyNodeChanges, applyEdgeChanges,
  type Edge, type EdgeChange, type Node, type NodeChange, type ReactFlowInstance,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { nodeTypes } from './nodes/CustomNodes';
import { edgeTypes } from './edges/CustomEdges';
import { applyLayout } from './layout';
import type { TopologyEdge, TopologyNode } from '@/types';
import { getInternetPath, getTopology } from '@/api/topology';

interface TopologyCanvasProps {
  projectId: string;
  refreshKey?: number;
  onNodeClick?: (node: TopologyNode | null) => void;
  onEdgeClick?: (edge: TopologyEdge | null) => void;
}

function topologyNode(data: unknown): TopologyNode {
  return data as TopologyNode;
}

function topologyEdge(edge: Edge): TopologyEdge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    relationship: (edge.data?.relationship as TopologyEdge['relationship']) || 'attached_to',
    inferred: edge.type === 'inferred',
    confidence: Number(edge.data?.confidence) || 1,
    properties: edge.data || {},
  };
}

const TopologyCanvas: React.FC<TopologyCanvasProps> = ({
  projectId, refreshKey = 0, onNodeClick, onEdgeClick,
}) => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [highlightedPath, setHighlightedPath] = useState<string[]>([]);
  const flow = useRef<ReactFlowInstance<Node, Edge> | null>(null);
  const requestSequence = useRef(0);

  useEffect(() => {
    if (!projectId) {
      setNodes([]);
      setEdges([]);
      setLoading(false);
      return;
    }
    const sequence = ++requestSequence.current;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const topology = await getTopology(projectId);
        const layout = await applyLayout(topology.nodes, topology.edges);
        if (sequence !== requestSequence.current) return;
        setNodes(layout.nodes);
        setEdges(layout.edges);
        setHighlightedPath([]);
        requestAnimationFrame(() => flow.current?.fitView({ padding: 0.12, duration: 350 }));
      } catch (err) {
        console.error('Failed to load topology:', err);
        if (sequence === requestSequence.current) setError('Failed to load topology data');
      } finally {
        if (sequence === requestSequence.current) setLoading(false);
      }
    };
    load();
  }, [projectId, refreshKey]);

  const highlightServerPath = useCallback(async (serverId: string, fallbackNodeId?: string) => {
    try {
      const result = await getInternetPath(serverId);
      if (result.found) {
        setHighlightedPath(result.path);
        return;
      }
    } catch (err) {
      console.error('Failed to get internet path:', err);
    }
    if (fallbackNodeId) {
      const direct = edges
        .filter((edge) => edge.source === fallbackNodeId || edge.target === fallbackNodeId)
        .flatMap((edge) => [edge.source, edge.target]);
      setHighlightedPath([...new Set([fallbackNodeId, ...direct])]);
    } else {
      setHighlightedPath([]);
    }
  }, [edges]);

  const focusIds = useMemo(
    () => new Set(highlightedPath),
    [highlightedPath],
  );
  const styledNodes = useMemo(() => {
    if (focusIds.size === 0) return nodes;
    const focusedParents = new Set(
      nodes.filter((node) => focusIds.has(node.id) && node.parentId).map((node) => node.parentId as string),
    );
    return nodes.map((node) => ({
      ...node,
      style: {
        ...node.style,
        opacity: focusIds.has(node.id) || focusedParents.has(node.id) ? 1 : 0.18,
      },
    }));
  }, [nodes, focusIds]);

  const styledEdges = useMemo(() => {
    if (focusIds.size === 0) return edges;
    return edges.map((edge) => {
      const focused = focusIds.has(edge.source) && focusIds.has(edge.target);
      return {
        ...edge,
        style: {
          ...edge.style,
          opacity: focused ? 1 : 0.12,
          stroke: focused ? '#2563eb' : edge.style?.stroke,
          strokeWidth: focused ? 2.4 : edge.style?.strokeWidth,
        },
      };
    });
  }, [edges, focusIds]);

  const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    const selected = topologyNode(node.data);
    if (selected.properties.metadata?.synthetic) return;
    onNodeClick?.(selected);
    if (selected.resource_type === 'server') highlightServerPath(selected.resource_id, node.id);
    else setHighlightedPath([node.id]);
  }, [highlightServerPath, onNodeClick]);

  const handlePaneClick = useCallback(() => {
    setHighlightedPath([]);
    onNodeClick?.(null);
  }, [onNodeClick]);

  if (loading) return <div className="flex h-full items-center justify-center bg-slate-50 text-sm text-slate-500">Loading topology…</div>;
  if (error) return <div className="flex h-full items-center justify-center bg-slate-50 text-sm text-red-600">{error}</div>;

  return (
    <div className="h-full w-full bg-slate-50">
      <ReactFlow
        nodes={styledNodes}
        edges={styledEdges}
        onInit={(instance) => { flow.current = instance; }}
        onNodesChange={(changes: NodeChange[]) => setNodes((current) => applyNodeChanges(changes, current))}
        onEdgesChange={(changes: EdgeChange[]) => setEdges((current) => applyEdgeChanges(changes, current))}
        onNodeClick={handleNodeClick}
        onEdgeClick={(_event, edge) => onEdgeClick?.(topologyEdge(edge))}
        onPaneClick={handlePaneClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        minZoom={0.08}
        maxZoom={2}
        defaultEdgeOptions={{ type: 'confirmed' }}
        nodesDraggable={false}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#dbe2ea" />
        <Controls showInteractive={false} className="!border-slate-200 !shadow-sm" />
        <MiniMap
          pannable
          zoomable
          className="!h-24 !w-36 !border !border-slate-200 !bg-white !shadow-none"
          nodeColor={(node) => {
            const data = topologyNode(node.data);
            if (data.resource_type === 'network') return data.properties.is_external ? '#5eead4' : '#cbd5e1';
            if (data.resource_type === 'router') return '#c4b5fd';
            if (data.resource_type === 'internet') return '#67e8f9';
            return data.role === 'firewall' ? '#fda4af' : '#93c5fd';
          }}
          maskColor="rgba(248, 250, 252, 0.72)"
        />
      </ReactFlow>
    </div>
  );
};

export default TopologyCanvas;
