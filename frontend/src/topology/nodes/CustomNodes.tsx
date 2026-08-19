/** Compact operational nodes for the single Traffic Topology. */
import React, { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { TopologyNode } from '@/types';

function topologyNode(data: unknown): TopologyNode {
  return data as TopologyNode;
}

const StatusDot: React.FC<{ status: string }> = ({ status }) => {
  const color = status === 'ACTIVE'
    ? 'bg-emerald-500'
    : status === 'ERROR' ? 'bg-red-500' : 'bg-slate-400';
  return <span title={status} className={`inline-block h-2 w-2 shrink-0 rounded-full ${color}`} />;
};

const TrafficHandles = ({ color = '!bg-slate-400' }: { color?: string }) => (
  <>
    <Handle type="target" position={Position.Left} className={`!h-2 !w-2 ${color}`} />
    <Handle type="source" position={Position.Right} className={`!h-2 !w-2 ${color}`} />
  </>
);

function externalInterface(node: TopologyNode) {
  return Object.values(node.properties.interfaces || {}).find(
    (networkInterface) => networkInterface.is_external || networkInterface.role === 'WAN',
  );
}

export const ServerNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = topologyNode(data);
  const ips = node.properties.ips || [];
  return (
    <div
      className="traffic-vm"
      title={`${node.status}${node.project_name ? ` · ${node.project_name}` : ''}${node.properties.floating_ips?.length ? ` · FIP ${node.properties.floating_ips.join(', ')}` : ''}`}
    >
      <TrafficHandles />
      <div className="flex min-w-0 items-center gap-2">
        <StatusDot status={node.status} />
        <span className="truncate text-xs font-semibold text-slate-800">{node.name}</span>
      </div>
      <div className="mt-1 truncate pl-4 font-mono text-[11px] text-slate-500">
        {ips[0] || 'No fixed IP'}{ips.length > 1 ? `  +${ips.length - 1}` : ''}
      </div>
    </div>
  );
});
ServerNode.displayName = 'ServerNode';

export const FirewallNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = topologyNode(data);
  const wan = externalInterface(node);
  return (
    <div className="traffic-vm border-l-2 border-l-rose-400" title={`${node.status} · OpenStack appliance VM`}>
      <TrafficHandles color="!bg-rose-400" />
      <div className="flex min-w-0 items-center gap-2">
        <StatusDot status={node.status} />
        <span className="truncate text-xs font-semibold text-slate-800">{node.name}</span>
        <span className="ml-auto text-[9px] uppercase tracking-wide text-rose-500">FW VM</span>
      </div>
      <div
        className="mt-1 truncate pl-4 font-mono text-[11px] text-rose-600"
        title={wan ? `External Network: ${wan.network_name || wan.network_id}` : undefined}
      >
        {wan?.ip_addresses?.[0] ? `WAN ${wan.ip_addresses[0]}` : 'No WAN interface'}
      </div>
    </div>
  );
});
FirewallNode.displayName = 'FirewallNode';

export const ApplianceNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = topologyNode(data);
  const wan = externalInterface(node);
  return (
    <div className="traffic-vm border-l-2 border-l-violet-400" title={`${node.status} · OpenStack router VM`}>
      <TrafficHandles color="!bg-violet-400" />
      <div className="flex min-w-0 items-center gap-2">
        <StatusDot status={node.status} />
        <span className="truncate text-xs font-semibold text-slate-800">{node.name}</span>
        <span className="ml-auto text-[9px] uppercase tracking-wide text-violet-500">Router VM</span>
      </div>
      <div className="mt-1 truncate pl-4 font-mono text-[11px] text-violet-600">
        {wan?.ip_addresses?.[0] ? `WAN ${wan.ip_addresses[0]}` : 'No WAN interface'}
      </div>
    </div>
  );
});
ApplianceNode.displayName = 'ApplianceNode';

export const NetworkGroupNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = topologyNode(data);
  const external = node.properties.is_external;
  const synthetic = Boolean(node.properties.metadata?.synthetic);
  return (
    <div className={`traffic-network-group ${external ? 'traffic-network-external' : ''} ${synthetic ? 'traffic-network-unknown' : ''}`}>
      <TrafficHandles color={external ? '!bg-teal-500' : '!bg-slate-400'} />
      <div className="flex items-start justify-between gap-3 px-4 pt-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-800" title={node.name}>{node.name}</div>
          <div className="mt-0.5 truncate font-mono text-[11px] text-slate-500">
            {node.properties.cidr || (synthetic ? 'No Neutron network attachment' : 'No subnet')}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2 text-[10px] text-slate-500">
          {node.properties.provider_segmentation_id != null && <span>VLAN {node.properties.provider_segmentation_id}</span>}
          {node.properties.is_shared && <span className="rounded bg-violet-50 px-1.5 py-0.5 text-violet-600">Shared</span>}
          {external && <span className="rounded bg-teal-50 px-1.5 py-0.5 text-teal-700">External</span>}
        </div>
      </div>
    </div>
  );
});
NetworkGroupNode.displayName = 'NetworkGroupNode';

export const RouterNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = topologyNode(data);
  const gateway = node.properties.external_gateway;
  return (
    <div
      className="traffic-device border-l-2 border-l-violet-400"
      title={gateway ? `External Network: ${gateway.network_name || gateway.network_id}${gateway.subnet_cidr ? ` · ${gateway.subnet_cidr}` : ''}` : undefined}
    >
      <TrafficHandles color="!bg-violet-400" />
      <div className="truncate text-xs font-semibold text-slate-800" title={node.name}>{node.name}</div>
      <div className="mt-1 text-[10px] uppercase tracking-wide text-violet-600">Neutron Router</div>
      <div className="mt-1.5 truncate font-mono text-[11px] text-slate-600">
        {gateway?.ip_address ? `WAN ${gateway.ip_address}` : gateway ? 'WAN IP unavailable' : 'No external gateway'}
      </div>
    </div>
  );
});
RouterNode.displayName = 'RouterNode';

export const InternetNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = topologyNode(data);
  return (
    <div className="traffic-device border-l-2 border-l-cyan-400 bg-cyan-50/50">
      <TrafficHandles color="!bg-cyan-400" />
      <div className="truncate text-xs font-semibold text-cyan-900">{node.name}</div>
      <div className="mt-1 text-[10px] uppercase tracking-wide text-cyan-600">Logical destination</div>
    </div>
  );
});
InternetNode.displayName = 'InternetNode';

export const DefaultNode: React.FC<NodeProps> = memo(({ data }) => {
  const node = topologyNode(data);
  return <div className="traffic-device"><TrafficHandles /><div className="truncate text-xs font-medium">{node.name}</div></div>;
});
DefaultNode.displayName = 'DefaultNode';

export const nodeTypes = {
  server: ServerNode,
  firewall: FirewallNode,
  appliance: ApplianceNode,
  networkGroup: NetworkGroupNode,
  router: RouterNode,
  internet: InternetNode,
  default: DefaultNode,
};
