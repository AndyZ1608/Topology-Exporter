/**
 * Custom edge components for React Flow.
 */
import React from 'react';
import { BaseEdge, EdgeProps, getBezierPath, getStraightPath } from '@xyflow/react';

// Confirmed edge (solid line)
export const ConfirmedEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
}) => {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <BaseEdge
      id={id}
      path={edgePath}
      style={{
        ...style,
        stroke: '#374151',
        strokeWidth: 2,
      }}
      markerEnd={markerEnd}
    />
  );
};

// Inferred edge (dashed line)
export const InferredEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
}) => {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <BaseEdge
      id={id}
      path={edgePath}
      style={{
        ...style,
        stroke: '#9ca3af',
        strokeWidth: 1.5,
        strokeDasharray: '5,5',
      }}
      markerEnd={markerEnd}
    />
  );
};

// Floating IP edge with special styling
export const FloatingIpEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
}) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const floatingIp = data && typeof data === 'object' ? (data as Record<string, unknown>).floating_ip : null;

  if (floatingIp && typeof labelX === 'number' && typeof labelY === 'number') {
    return (
      <>
        <BaseEdge
          id={id}
          path={edgePath}
          style={{
            ...style,
            stroke: '#06b6d4',
            strokeWidth: 1.5,
            strokeDasharray: '3,3',
          }}
          markerEnd={markerEnd}
        />
        <foreignObject
          x={labelX - 50}
          y={labelY - 10}
          width={100}
          height={20}
          className="overflow-visible"
        >
          <div className="text-xs text-cyan-600 bg-cyan-50 px-1 rounded text-center">
            {String(floatingIp)}
          </div>
        </foreignObject>
      </>
    );
  }

  return (
    <BaseEdge
      id={id}
      path={edgePath}
      style={{
        ...style,
        stroke: '#06b6d4',
        strokeWidth: 1.5,
        strokeDasharray: '3,3',
      }}
      markerEnd={markerEnd}
    />
  );
};

// Trunk subport edge
export const TrunkSubportEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  style = {},
  markerEnd,
  data,
}) => {
  const [edgePath, labelX, labelY] = getStraightPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  });

  const vlanId = data && typeof data === 'object' ? (data as Record<string, unknown>).vlan_id : null;

  if (vlanId && typeof labelX === 'number' && typeof labelY === 'number') {
    return (
      <>
        <BaseEdge
          id={id}
          path={edgePath}
          style={{
            ...style,
            stroke: '#f97316',
            strokeWidth: 1.5,
          }}
          markerEnd={markerEnd}
        />
        <foreignObject
          x={labelX - 25}
          y={labelY - 10}
          width={50}
          height={20}
          className="overflow-visible"
        >
          <div className="text-xs text-orange-600 bg-orange-50 px-1 rounded text-center">
            VLAN {String(vlanId)}
          </div>
        </foreignObject>
      </>
    );
  }

  return (
    <BaseEdge
      id={id}
      path={edgePath}
      style={{
        ...style,
        stroke: '#f97316',
        strokeWidth: 1.5,
      }}
      markerEnd={markerEnd}
    />
  );
};

// HA member edge
export const HAMemberEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  style = {},
  markerEnd,
}) => {
  const [edgePath] = getStraightPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  });

  return (
    <BaseEdge
      id={id}
      path={edgePath}
      style={{
        ...style,
        stroke: '#f97316',
        strokeWidth: 2,
      }}
      markerEnd={markerEnd}
    />
  );
};

// Internet uplink edge
export const InternetUplinkEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
}) => {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <BaseEdge
      id={id}
      path={edgePath}
      style={{
        ...style,
        stroke: '#06b6d4',
        strokeWidth: 2,
        strokeDasharray: '8,4',
      }}
      markerEnd={markerEnd}
    />
  );
};

// Export all edge types - using eslint disable for complex React Flow typing
/* eslint-disable @typescript-eslint/no-explicit-any */
export const edgeTypes: Record<string, React.ComponentType<any>> = {
  confirmed: ConfirmedEdge,
  inferred: InferredEdge,
  floating_ip: FloatingIpEdge,
  trunk_subport: TrunkSubportEdge,
  ha_member: HAMemberEdge,
  internet_uplink: InternetUplinkEdge,
};
/* eslint-enable @typescript-eslint/no-explicit-any */
