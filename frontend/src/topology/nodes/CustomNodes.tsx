/**
 * Custom node components for React Flow.
 */
import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import type { TopologyNode } from '@/types';

// Status badge component
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const statusColors: Record<string, string> = {
    ACTIVE: 'bg-green-100 text-green-700',
    SHUTOFF: 'bg-gray-100 text-gray-600',
    ERROR: 'bg-red-100 text-red-700',
    UNKNOWN: 'bg-gray-100 text-gray-500',
  };

  return (
    <span className={`text-xs px-1.5 py-0.5 rounded ${statusColors[status] || statusColors.UNKNOWN}`}>
      {status}
    </span>
  );
};

// Server/VM Node
export const ServerNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = data as TopologyNode;

  return (
    <div className="node-card node-card-server">
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />

      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="font-medium text-gray-900 truncate" title={node.name}>
            {node.name}
          </div>
          <StatusBadge status={node.status} />
        </div>
        <div className="text-xs text-gray-500 whitespace-nowrap">
          {node.role.toUpperCase()}
        </div>
      </div>

      {node.properties.ips && node.properties.ips.length > 0 && (
        <div className="mt-2 text-xs text-gray-600 font-mono">
          {node.properties.ips[0]}
          {node.properties.ips.length > 1 && (
            <span className="text-gray-400"> +{node.properties.ips.length - 1}</span>
          )}
        </div>
      )}

      {node.project_name && (
        <div className="mt-1 text-xs text-gray-400 truncate" title={node.project_name}>
          {node.project_name}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-gray-400" />
    </div>
  );
});
ServerNode.displayName = 'ServerNode';

// Firewall Node
export const FirewallNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = data as TopologyNode;
  const interfaces = node.properties.interfaces || {};

  return (
    <div className="node-card node-card-firewall">
      <Handle type="target" position={Position.Top} className="!bg-red-400" />

      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-gray-900 truncate" title={node.name}>
            {node.name}
          </div>
          <div className="text-xs text-red-600">
            {node.properties.metadata?.vendor || 'Firewall'}
          </div>
        </div>
        <StatusBadge status={node.status} />
      </div>

      {/* Interfaces */}
      {Object.entries(interfaces).length > 0 && (
        <div className="mt-2 space-y-1">
          {Object.entries(interfaces).slice(0, 4).map(([role, info]) => (
            <div key={role} className="flex items-center gap-1 text-xs">
              <span className={`px-1 rounded text-white text-[10px] font-medium ${
                role === 'WAN' ? 'bg-blue-500' :
                role === 'LAN' ? 'bg-green-500' :
                role === 'MGMT' ? 'bg-purple-500' :
                role === 'TRUNK' ? 'bg-orange-500' :
                'bg-gray-500'
              }`}>
                {role}
              </span>
              <span className="text-gray-600 font-mono truncate">
                {typeof info === 'string' ? info : (info as { ip_addresses?: string[] })?.ip_addresses?.[0] || '—'}
              </span>
            </div>
          ))}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-red-400" />
    </div>
  );
});
FirewallNode.displayName = 'FirewallNode';

// Network Node
export const NetworkNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = data as TopologyNode;

  return (
    <div className="node-card node-card-network">
      <Handle type="target" position={Position.Top} className="!bg-green-400" />

      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="font-medium text-gray-900 truncate" title={node.name}>
            {node.name}
          </div>
          {node.properties.cidr && (
            <div className="text-xs text-gray-500 font-mono truncate">
              {node.properties.cidr}
            </div>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <StatusBadge status={node.status} />
          {node.properties.is_external && (
            <span className="text-xs px-1 py-0.5 rounded bg-cyan-100 text-cyan-700">
              External
            </span>
          )}
        </div>
      </div>

      {node.properties.provider_segmentation_id && (
        <div className="mt-1 text-xs text-gray-400">
          VLAN {node.properties.provider_segmentation_id}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-green-400" />
    </div>
  );
});
NetworkNode.displayName = 'NetworkNode';

// Router Node
export const RouterNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = data as TopologyNode;

  return (
    <div className="node-card node-card-router">
      <Handle type="target" position={Position.Top} className="!bg-purple-400" />

      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="font-medium text-gray-900 truncate" title={node.name}>
            {node.name}
          </div>
          <div className="text-xs text-purple-600">Router</div>
        </div>
        <StatusBadge status={node.status} />
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-purple-400" />
    </div>
  );
});
RouterNode.displayName = 'RouterNode';

// HA Group Node
export const HAGroupNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = data as TopologyNode;
  const members = node.properties.ha_members || [];

  return (
    <div className="node-card border-l-4 border-l-orange-500 min-w-[200px]">
      <Handle type="target" position={Position.Top} className="!bg-orange-400" />

      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">🔥</span>
        <div>
          <div className="font-semibold text-gray-900">{node.name}</div>
          <div className="text-xs text-orange-600">HA Group</div>
        </div>
      </div>

      <div className="flex flex-wrap gap-1">
        {members.map((member, idx) => (
          <span key={idx} className="text-xs bg-orange-50 text-orange-700 px-1.5 py-0.5 rounded">
            {member}
          </span>
        ))}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-orange-400" />
    </div>
  );
});
HAGroupNode.displayName = 'HAGroupNode';

// Internet Node
export const InternetNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = data as TopologyNode;

  return (
    <div className="node-card node-card-internet bg-gradient-to-br from-cyan-50 to-blue-50">
      <Handle type="target" position={Position.Top} className="!bg-cyan-400" />

      <div className="flex items-center gap-2">
        <span className="text-2xl">☁️</span>
        <div>
          <div className="font-semibold text-cyan-900">{node.name}</div>
          <div className="text-xs text-cyan-600">Internet</div>
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-cyan-400" />
    </div>
  );
});
InternetNode.displayName = 'InternetNode';

// Subnet Node
export const SubnetNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = data as TopologyNode;

  return (
    <div className="node-card border-l-4 border-l-teal-400 min-w-[150px]">
      <Handle type="target" position={Position.Top} className="!bg-teal-400" />

      <div className="font-medium text-gray-800 truncate" title={node.name}>
        {node.name}
      </div>
      {node.properties.cidr && (
        <div className="text-xs text-gray-500 font-mono">{node.properties.cidr}</div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-teal-400" />
    </div>
  );
});
SubnetNode.displayName = 'SubnetNode';

// Default/Unknown Node
export const DefaultNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = data as TopologyNode;

  return (
    <div className="node-card border-l-4 border-l-gray-400">
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />

      <div className="font-medium text-gray-700 truncate">{node.name}</div>
      <div className="text-xs text-gray-500">{node.role}</div>

      <Handle type="source" position={Position.Bottom} className="!bg-gray-400" />
    </div>
  );
});
DefaultNode.displayName = 'DefaultNode';

// Export all node types
export const nodeTypes = {
  server: ServerNode,
  firewall: FirewallNode,
  network: NetworkNode,
  router: RouterNode,
  hagroup: HAGroupNode,
  internet: InternetNode,
  subnet: SubnetNode,
  default: DefaultNode,
};
