/**
 * Details drawer component for node details.
 */
import React, { useEffect, useState } from 'react';
import type { TopologyNode, InternetPathResponse } from '@/types';
import { getInternetPath, getNodeConnections } from '@/api/topology';

interface DetailsDrawerProps {
  node: TopologyNode | null;
  onClose: () => void;
}

// Connection types
interface Connection {
  source: string;
  target: string;
  relationship: string;
}

interface Connections {
  inbound: Connection[];
  outbound: Connection[];
}

const DetailsDrawer: React.FC<DetailsDrawerProps> = ({ node, onClose }) => {
  const [internetPath, setInternetPath] = useState<InternetPathResponse | null>(null);
  const [connections, setConnections] = useState<Connections | null>(null);
  const [loading, setLoading] = useState(false);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const typedSetConnections = (conns: any) => {
    if (conns && typeof conns === 'object' && !Array.isArray(conns)) {
      setConnections(conns as Connections);
    }
  };

  useEffect(() => {
    if (node) {
      loadDetails();
    } else {
      setInternetPath(null);
      setConnections(null);
    }
  }, [node]);

  const loadDetails = async () => {
    if (!node) return;

    setLoading(true);
    try {
      // Load connections
      const conns = await getNodeConnections(node.id);
      typedSetConnections(conns);

      // If server, load internet path
      if (node.resource_type === 'server') {
        const path = await getInternetPath(node.resource_id);
        setInternetPath(path);
      }
    } catch (err) {
      console.error('Failed to load details:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!node) {
    return null;
  }

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'ACTIVE':
        return 'bg-green-100 text-green-700';
      case 'SHUTOFF':
        return 'bg-gray-100 text-gray-600';
      case 'ERROR':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  const getRoleIcon = (role: string): string => {
    switch (role) {
      case 'vm':
        return '🖥️';
      case 'firewall':
        return '🔥';
      case 'router':
        return '🔀';
      case 'network':
        return '🌐';
      case 'internet':
        return '☁️';
      case 'ha_group':
        return '🔗';
      default:
        return '📦';
    }
  };

  return (
    <div className="w-96 bg-white border-l border-gray-200 overflow-y-auto animate-slideIn">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">{getRoleIcon(node.role)}</span>
          <h2 className="font-semibold text-gray-900">{node.name}</h2>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-6">
        {/* Basic Info */}
        <section>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Information</h3>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">ID</dt>
              <dd className="text-gray-900 font-mono text-xs truncate max-w-[200px]" title={node.resource_id}>
                {node.resource_id.slice(0, 8)}...
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Type</dt>
              <dd className="text-gray-900 capitalize">{node.resource_type}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Role</dt>
              <dd className="text-gray-900 capitalize">{node.role}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Status</dt>
              <dd>
                <span className={`px-2 py-0.5 rounded-full text-xs ${getStatusColor(node.status)}`}>
                  {node.status}
                </span>
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Layer</dt>
              <dd className="text-gray-900 capitalize">{node.layer}</dd>
            </div>
            {node.project_name && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Project</dt>
                <dd className="text-gray-900">{node.project_name}</dd>
              </div>
            )}
          </dl>
        </section>

        {/* Server-specific info */}
        {node.resource_type === 'server' && (
          <>
            {/* IPs */}
            {node.properties.ips && node.properties.ips.length > 0 && (
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">IP Addresses</h3>
                <div className="space-y-1">
                  {node.properties.ips.map((ip, idx) => (
                    <div key={idx} className="text-sm font-mono bg-gray-50 px-2 py-1 rounded">
                      {ip}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* MAC Addresses */}
            {node.properties.mac_addresses && node.properties.mac_addresses.length > 0 && (
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">MAC Addresses</h3>
                <div className="space-y-1">
                  {node.properties.mac_addresses.map((mac, idx) => (
                    <div key={idx} className="text-sm font-mono text-gray-600">
                      {mac}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Flavor */}
            {node.properties.flavor && (
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Flavor</h3>
                <div className="text-sm text-gray-900">{node.properties.flavor}</div>
              </section>
            )}

            {/* Floating IPs */}
            {node.properties.floating_ips && node.properties.floating_ips.length > 0 && (
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Floating IPs</h3>
                <div className="space-y-1">
                  {node.properties.floating_ips.map((fip, idx) => (
                    <div key={idx} className="text-sm font-mono bg-cyan-50 text-cyan-700 px-2 py-1 rounded">
                      {fip}
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}

        {/* Network-specific info */}
        {node.resource_type === 'network' && (
          <>
            {/* CIDR */}
            {node.properties.cidr && (
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">CIDR</h3>
                <div className="text-sm font-mono bg-gray-50 px-2 py-1 rounded">
                  {node.properties.cidr}
                </div>
              </section>
            )}

            {/* Gateway */}
            {node.properties.gateway_ip && (
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Gateway</h3>
                <div className="text-sm font-mono text-gray-900">{node.properties.gateway_ip}</div>
              </section>
            )}

            {/* Provider Info */}
            {(node.properties.provider_network_type || node.properties.provider_physical_network) && (
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Provider</h3>
                <dl className="space-y-1 text-sm">
                  {node.properties.provider_network_type && (
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Type</dt>
                      <dd className="text-gray-900">{node.properties.provider_network_type}</dd>
                    </div>
                  )}
                  {node.properties.provider_physical_network && (
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Physical</dt>
                      <dd className="text-gray-900">{node.properties.provider_physical_network}</dd>
                    </div>
                  )}
                  {node.properties.provider_segmentation_id && (
                    <div className="flex justify-between">
                      <dt className="text-gray-500">VLAN ID</dt>
                      <dd className="text-gray-900">{node.properties.provider_segmentation_id}</dd>
                    </div>
                  )}
                </dl>
              </section>
            )}

            {/* Flags */}
            <section>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Properties</h3>
              <div className="flex flex-wrap gap-1">
                {node.properties.is_external && (
                  <span className="px-2 py-0.5 text-xs bg-cyan-100 text-cyan-700 rounded">External</span>
                )}
                {node.properties.is_shared && (
                  <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded">Shared</span>
                )}
              </div>
            </section>
          </>
        )}

        {/* Firewall-specific info */}
        {node.role === 'firewall' && (
          <>
            {/* Vendor */}
            {node.properties.metadata?.vendor && (
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Vendor</h3>
                <div className="text-sm text-gray-900">{node.properties.metadata.vendor}</div>
              </section>
            )}

            {/* HA Group */}
            {node.properties.metadata?.ha_group && (
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">HA Group</h3>
                <div className="text-sm text-orange-700 bg-orange-50 px-2 py-1 rounded inline-block">
                  {node.properties.metadata.ha_group}
                </div>
              </section>
            )}

            {/* Interfaces */}
            {Object.keys(node.properties.interfaces || {}).length > 0 && (
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Interfaces</h3>
                <div className="space-y-2">
                  {Object.entries(node.properties.interfaces).map(([portId, info]) => {
                    const ifaceInfo = info as { role?: string; ip_addresses?: string[] };
                    return (
                      <div key={portId} className="flex items-center gap-2 text-sm">
                        <span className={`px-1.5 py-0.5 rounded text-white text-xs font-medium ${
                          ifaceInfo.role === 'WAN' ? 'bg-blue-500' :
                          ifaceInfo.role === 'LAN' ? 'bg-green-500' :
                          ifaceInfo.role === 'MGMT' ? 'bg-purple-500' :
                          ifaceInfo.role === 'TRUNK' ? 'bg-orange-500' :
                          'bg-gray-500'
                        }`}>
                          {ifaceInfo.role || 'UNKNOWN'}
                        </span>
                        {ifaceInfo.ip_addresses && ifaceInfo.ip_addresses.length > 0 && (
                          <span className="font-mono text-gray-600">{ifaceInfo.ip_addresses[0]}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            )}
          </>
        )}

        {/* Internet Path */}
        {node.resource_type === 'server' && (
          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Internet Path</h3>
            {loading ? (
              <div className="text-sm text-gray-500">Loading...</div>
            ) : internetPath ? (
              internetPath.found ? (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${
                      internetPath.inferred ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'
                    }`}>
                      {internetPath.inferred ? 'Inferred' : 'Confirmed'}
                    </span>
                    <span className="text-xs text-gray-500">
                      Confidence: {Math.round(internetPath.confidence * 100)}%
                    </span>
                  </div>
                  <div className="space-y-1">
                    {internetPath.path.map((nodeId, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-sm">
                        <span className="text-gray-300">↓</span>
                        <span className={nodeId === 'internet' ? 'text-cyan-600 font-medium' : 'text-gray-700'}>
                          {nodeId === 'internet' ? 'Internet' :
                           internetPath.path_nodes[idx]?.name || nodeId}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-500">
                  {internetPath.reason || 'No path to Internet found'}
                </div>
              )
            ) : (
              <div className="text-sm text-gray-500">Unable to determine Internet path</div>
            )}
          </section>
        )}

        {/* Connections */}
        {connections && (
          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Connections</h3>
            <div className="space-y-2 text-sm">
              {connections.inbound?.length > 0 && (
                <div>
                  <div className="text-xs text-gray-500 mb-1">Inbound ({connections.inbound.length})</div>
                  <div className="space-y-1">
                    {connections.inbound.slice(0, 5).map((conn, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-xs">
                        <span className="text-gray-400">←</span>
                        <span className="text-gray-600 truncate">{conn.source.split(':')[1]?.slice(0, 8) || conn.source}</span>
                        <span className="text-gray-400">({conn.relationship})</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {connections.outbound?.length > 0 && (
                <div>
                  <div className="text-xs text-gray-500 mb-1">Outbound ({connections.outbound.length})</div>
                  <div className="space-y-1">
                    {connections.outbound.slice(0, 5).map((conn, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-xs">
                        <span className="text-gray-400">→</span>
                        <span className="text-gray-600 truncate">{conn.target.split(':')[1]?.slice(0, 8) || conn.target}</span>
                        <span className="text-gray-400">({conn.relationship})</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Tags */}
        {node.tags && node.tags.length > 0 && (
          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Tags</h3>
            <div className="flex flex-wrap gap-1">
              {node.tags.map((tag, idx) => (
                <span key={idx} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                  {tag}
                </span>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
};

export default DetailsDrawer;
