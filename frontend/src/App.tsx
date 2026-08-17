/**
 * Main App component.
 */
import React, { useState, useEffect, useCallback } from 'react';
import TopologyCanvas from './topology/TopologyCanvas';
import Sidebar from './components/Sidebar';
import DetailsDrawer from './components/DetailsDrawer';
import Header from './components/Header';
import type { TopologyFilters, TopologyNode, SyncStatus } from './types';
import { getSyncStatus, refreshTopology } from './api/topology';

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
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Poll sync status
  useEffect(() => {
    const pollStatus = async () => {
      try {
        const status = await getSyncStatus();
        setSyncStatus(status);
      } catch (err) {
        console.error('Failed to get sync status:', err);
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, 5000);

    return () => clearInterval(interval);
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
