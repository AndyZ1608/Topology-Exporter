/** Main application shell. */
import React, { useCallback, useEffect, useState } from 'react';
import TopologyCanvas from './topology/TopologyCanvas';
import Sidebar from './components/Sidebar';
import DetailsDrawer from './components/DetailsDrawer';
import Header from './components/Header';
import type { CloudSummary, TopologyNode, SyncStatus } from './types';
import { getCloudSummary, getSyncStatus, refreshTopology } from './api/topology';

const App: React.FC = () => {
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [projectSummary, setProjectSummary] = useState<CloudSummary | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    getSyncStatus()
      .then(setSyncStatus)
      .catch((error) => console.error('Failed to get sync status:', error));
  }, []);

  useEffect(() => {
    let active = true;
    setProjectSummary(null);
    if (!selectedProjectId) return () => { active = false; };

    getCloudSummary(selectedProjectId)
      .then((summary) => { if (active) setProjectSummary(summary); })
      .catch((error) => console.error('Failed to load project summary:', error));
    return () => { active = false; };
  }, [selectedProjectId, refreshKey]);

  const handleProjectChange = useCallback((projectId: string) => {
    setSelectedNode(null);
    setSelectedProjectId(projectId);
  }, []);

  const handleNodeSelect = useCallback((node: TopologyNode | null) => {
    setSelectedNode(node);
  }, []);

  const handleRefresh = useCallback(async () => {
    try {
      await refreshTopology();
      setSyncStatus(await getSyncStatus());
      setRefreshKey((value) => value + 1);
    } catch (error) {
      console.error('Failed to refresh topology:', error);
    }
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarOpen((open) => !open);
  }, []);

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      <Header
        syncStatus={syncStatus}
        projectSummary={projectSummary}
        onRefresh={handleRefresh}
        onToggleSidebar={toggleSidebar}
        sidebarOpen={sidebarOpen}
      />

      <div className="flex flex-1 overflow-hidden">
        {sidebarOpen && (
          <Sidebar
            selectedProjectId={selectedProjectId}
            onProjectChange={handleProjectChange}
          />
        )}

        <main className="flex-1 overflow-hidden">
          <TopologyCanvas
            projectId={selectedProjectId}
            refreshKey={refreshKey}
            onNodeClick={handleNodeSelect}
          />
        </main>

        <DetailsDrawer
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      </div>
    </div>
  );
};

export default App;
