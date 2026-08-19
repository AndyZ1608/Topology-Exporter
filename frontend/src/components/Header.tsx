/**
 * Header component.
 */
import React from 'react';
import type { CloudSummary, SyncStatus } from '@/types';

interface HeaderProps {
  syncStatus: SyncStatus | null;
  projectSummary: CloudSummary | null;
  onRefresh: () => void;
  onToggleSidebar: () => void;
  sidebarOpen: boolean;
}

const Header: React.FC<HeaderProps> = ({
  syncStatus,
  projectSummary,
  onRefresh,
  onToggleSidebar,
  sidebarOpen,
}) => {
  const formatLastSync = (timestamp?: string): string => {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  const getStatusColor = (status?: string): string => {
    switch (status) {
      case 'success':
        return 'text-green-600';
      case 'syncing':
        return 'text-blue-600';
      case 'partial':
        return 'text-yellow-600';
      case 'failed':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusDot = (status?: string): string => {
    switch (status) {
      case 'success':
        return 'bg-green-500';
      case 'syncing':
        return 'bg-blue-500 animate-pulse';
      case 'partial':
        return 'bg-yellow-500';
      case 'failed':
        return 'bg-red-500';
      default:
        return 'bg-gray-400';
    }
  };

  return (
    <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-4">
        {/* Menu toggle */}
        <button
          onClick={onToggleSidebar}
          className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
          title={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {sidebarOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            )}
          </svg>
        </button>

        {/* Logo and title */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h1 className="text-base font-semibold text-gray-900">OpenStack Topology Explorer</h1>
        </div>
      </div>

      {projectSummary && (
        <div className="hidden items-center gap-6 text-xs lg:flex">
          {[
            [projectSummary.projects === 1 ? 'Project' : 'Projects', projectSummary.projects],
            [projectSummary.servers === 1 ? 'VM' : 'VMs', projectSummary.servers],
            [projectSummary.networks === 1 ? 'Network' : 'Networks', projectSummary.networks],
            [projectSummary.routers === 1 ? 'Router' : 'Routers', projectSummary.routers],
          ].map(([label, value]) => (
            <div key={String(label)} className="text-center">
              <div className="font-semibold text-gray-900">{value}</div>
              <div className="text-gray-500">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* Sync status */}
        <div className="flex items-center gap-2 text-sm">
          <div className={`w-2 h-2 rounded-full ${getStatusDot(syncStatus?.status)}`}></div>
          <span className={getStatusColor(syncStatus?.status)}>
            {syncStatus?.status === 'syncing' ? 'Syncing...' : `Sync: ${syncStatus?.status || 'unknown'}`}
          </span>
          <span className="text-gray-400">•</span>
          <span className="text-gray-500">Last: {formatLastSync(syncStatus?.last_sync)}</span>
        </div>

        {/* Refresh button */}
        <button
          onClick={onRefresh}
          disabled={syncStatus?.status === 'syncing'}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <svg className={`w-4 h-4 ${syncStatus?.status === 'syncing' ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>
    </header>
  );
};

export default Header;
