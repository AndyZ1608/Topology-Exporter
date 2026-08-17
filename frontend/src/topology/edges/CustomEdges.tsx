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
  data,
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
    <>
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
    </>
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
  data,
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
    <>
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
    </>
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
      {data?.floating_ip && (
        <foreignObject
          x={labelX - 50}
          y={labelY - 10}
          width={100}
          height={20}
          className="overflow-visible"
        >
          <div className="text-xs text-cyan-600 bg-cyan-50 px-1 rounded text-center">
            {data.floating_ip}
          </div>
        </foreignObject>
      )}
    </>
  );
};

// Trunk subport edge
export const TrunkSubportEdge: React.FC<EdgeProps> = ({
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
  const [edgePath, labelX, labelY] = getStraightPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

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
      {data?.vlan_id && (
        <foreignObject
          x={labelX - 25}
          y={labelY - 10}
          width={50}
          height={20}
          className="overflow-visible"
        >
          <div className="text-xs text-orange-600 bg-orange-50 px-1 rounded text-center">
            VLAN {data.vlan_id}
          </div>
        </foreignObject>
      )}
    </>
  );
};

// HA member edge
export const HAMemberEdge: React.FC<EdgeProps> = ({
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
  const [edgePath] = getStraightPath({
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
  data,
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

// Export all edge types
export const edgeTypes = {
  confirmed: ConfirmedEdge,
  inferred: InferredEdge,
  floating_ip: FloatingIpEdge,
  trunk_subport: TrunkSubportEdge,
  ha_member: HAMemberEdge,
  internet_uplink: InternetUplinkEdge,
};
