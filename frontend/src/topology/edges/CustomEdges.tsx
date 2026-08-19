/** Thin orthogonal edges matching ELK's architecture-diagram routing. */
import React from 'react';
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath, type EdgeProps } from '@xyflow/react';

const OrthogonalEdge: React.FC<EdgeProps & { inferred?: boolean }> = ({
  id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
  style = {}, markerEnd, inferred = false, data,
}) => {
  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
    borderRadius: 3, offset: 18,
  });
  const label = typeof data?.label === 'string' ? data.label : undefined;
  return <>
    <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        style={{
          ...style,
          stroke: inferred ? '#94a3b8' : '#64748b',
          strokeWidth: inferred ? 1.2 : 1.4,
          strokeDasharray: inferred ? '5 4' : undefined,
        }}
      />
    {label && (
      <EdgeLabelRenderer>
        <div
          className="pointer-events-none absolute rounded bg-white/90 px-1.5 py-0.5 font-mono text-[10px] text-slate-600 shadow-sm ring-1 ring-slate-200"
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
        >
          {label}
        </div>
      </EdgeLabelRenderer>
    )}
  </>;
};

export const ConfirmedEdge: React.FC<EdgeProps> = (props) => <OrthogonalEdge {...props} />;
export const InferredEdge: React.FC<EdgeProps> = (props) => <OrthogonalEdge {...props} inferred />;

/* eslint-disable @typescript-eslint/no-explicit-any */
export const edgeTypes: Record<string, React.ComponentType<any>> = {
  confirmed: ConfirmedEdge,
  inferred: InferredEdge,
};
/* eslint-enable @typescript-eslint/no-explicit-any */
