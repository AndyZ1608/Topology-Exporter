/**
 * Main App component.
 */
import React, { useState, useEffect, useCallback } from 'react';
import TopologyCanvas from './topology/TopologyCanvas';
import Sidebar from './components/Sidebar';
import DetailsDrawer from './components/DetailsDrawer';
import Header from './components/Header';
import type { CloudSummary, TopologyFilters, TopologyNode, SyncStatus } from './types';
import { getCloudSummary, getSyncStatus, refreshTopology } from './api/topology';

const App: React.FC = () => {
  const [filters, setFilters] = useState<TopologyFilters>({
    projectIds: [],
    resourceTypes: [],
    status: '',
    search: '',
    view: 'traffic',
  });

  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [cloudSummary, setCloudSummary] = useState<CloudSummary | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Load once. Further discovery is explicitly operator-triggered via Refresh.
  useEffect(() => {
    const loadStatus = async () => {
      try {
        const status = await getSyncStatus();
        setSyncStatus(status);
        setCloudSummary(await getCloudSummary());
      } catch (err) {
        console.error('Failed to get sync status:', err);
      }
    };

    loadStatus();
  }, []);

  // Handle filter changes
  const handleFiltersChange = useCallback((newFilters: TopologyFilters) => {
    setFilters(newFilters);
  }, []);

  // Handle node selection
  const handleNodeSelect = useCallback((node: TopologyNode | null) => {
    setSelectedNode(node);
  }, []);

  // Handle refresh
  const handleRefresh = useCallback(async () => {
    try {
      await refreshTopology();
      const status = await getSyncStatus();
      setSyncStatus(status);
      setCloudSummary(await getCloudSummary());
    } catch (err) {
      console.error('Failed to refresh topology:', err);
    }
  }, []);

  // Toggle sidebar
  const toggleSidebar = useCallback(() => {
    setSidebarOpen((prev) => !prev);
  }, []);

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <Header
        syncStatus={syncStatus}
        cloudSummary={cloudSummary}
        onRefresh={handleRefresh}
        onToggleSidebar={toggleSidebar}
        sidebarOpen={sidebarOpen}
      />

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        {sidebarOpen && (
          <Sidebar
            filters={filters}
            onFiltersChange={handleFiltersChange}
          />
        )}

        {/* Topology Canvas */}
        <main className="flex-1 overflow-hidden">
          <TopologyCanvas
            filters={filters}
            onNodeClick={handleNodeSelect}
          />
        </main>

        {/* Details Drawer */}
        <DetailsDrawer
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      </div>
    </div>
  );
};

export default App;
