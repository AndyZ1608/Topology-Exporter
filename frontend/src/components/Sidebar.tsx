/**
 * Sidebar component with filters.
 */
import React, { useState, useEffect } from 'react';
import type { TopologyFilters, Project } from '@/types';
import { getProjects } from '@/api/topology';

interface SidebarProps {
  filters: TopologyFilters;
  onFiltersChange: (filters: TopologyFilters) => void;
}

const RESOURCE_TYPES = [
  { value: 'server', label: 'VM' },
  { value: 'firewall', label: 'Firewall' },
  { value: 'router', label: 'Router' },
  { value: 'network', label: 'Network' },
  { value: 'ha_group', label: 'HA Group' },
];

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'ACTIVE', label: 'Active' },
  { value: 'SHUTOFF', label: 'Shutoff' },
  { value: 'ERROR', label: 'Error' },
];

const VIEW_OPTIONS = [
  { value: 'traffic', label: 'Traffic Path', description: 'VM → Network → Firewall → Internet' },
  { value: 'infrastructure', label: 'Infrastructure', description: 'Project → Network → Subnet → VM' },
  { value: 'project', label: 'Project', description: 'Internet → Shared → Project → Resources' },
];

const Sidebar: React.FC<SidebarProps> = ({ filters, onFiltersChange }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(true);

  // Load projects
  useEffect(() => {
    const loadProjects = async () => {
      try {
        const response = await getProjects();
        setProjects(response.projects);
      } catch (err) {
        console.error('Failed to load projects:', err);
      } finally {
        setLoadingProjects(false);
      }
    };

    loadProjects();
  }, []);

  // Handle project toggle
  const handleProjectToggle = (projectId: string) => {
    const newProjectIds = filters.projectIds.includes(projectId)
      ? filters.projectIds.filter((id) => id !== projectId)
      : [...filters.projectIds, projectId];
    onFiltersChange({ ...filters, projectIds: newProjectIds });
  };

  // Handle select all projects
  const handleSelectAllProjects = () => {
    if (filters.projectIds.length === projects.length) {
      onFiltersChange({ ...filters, projectIds: [] });
    } else {
      onFiltersChange({ ...filters, projectIds: projects.map((p) => p.id) });
    }
  };

  // Handle resource type toggle
  const handleResourceTypeToggle = (resourceType: string) => {
    const newTypes = filters.resourceTypes.includes(resourceType)
      ? filters.resourceTypes.filter((t) => t !== resourceType)
      : [...filters.resourceTypes, resourceType];
    onFiltersChange({ ...filters, resourceTypes: newTypes });
  };

  // Handle search change
  const handleSearchChange = (value: string) => {
    onFiltersChange({ ...filters, search: value });
  };

  // Handle view change
  const handleViewChange = (view: 'traffic' | 'infrastructure' | 'project') => {
    onFiltersChange({ ...filters, view });
  };

  // Handle status change
  const handleStatusChange = (status: string) => {
    onFiltersChange({ ...filters, status });
  };

  return (
    <aside className="w-72 bg-white border-r border-gray-200 overflow-y-auto">
      <div className="p-4 space-y-6">
        {/* Search */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1.5">Search</label>
          <div className="relative">
            <input
              type="text"
              value={filters.search}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Name, IP, UUID..."
              className="w-full pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
            />
            <svg
              className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        {/* View Mode */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-2">View Mode</label>
          <div className="space-y-1">
            {VIEW_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => handleViewChange(option.value as 'traffic' | 'infrastructure' | 'project')}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                  filters.view === option.value
                    ? 'bg-primary-50 text-primary-700 border border-primary-200'
                    : 'text-gray-700 hover:bg-gray-50 border border-transparent'
                }`}
              >
                <div className="font-medium">{option.label}</div>
                <div className="text-xs text-gray-500 mt-0.5">{option.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Projects */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-medium text-gray-700">Projects</label>
            <button
              onClick={handleSelectAllProjects}
              className="text-xs text-primary-600 hover:text-primary-700"
            >
              {filters.projectIds.length === projects.length ? 'Clear all' : 'Select all'}
            </button>
          </div>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {loadingProjects ? (
              <div className="text-sm text-gray-500 py-2">Loading...</div>
            ) : projects.length === 0 ? (
              <div className="text-sm text-gray-500 py-2">No projects found</div>
            ) : (
              projects.map((project) => (
                <label
                  key={project.id}
                  className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={filters.projectIds.includes(project.id)}
                    onChange={() => handleProjectToggle(project.id)}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-700 truncate">{project.name}</span>
                </label>
              ))
            )}
          </div>
        </div>

        {/* Resource Types */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-2">Resources</label>
          <div className="flex flex-wrap gap-1">
            {RESOURCE_TYPES.map((type) => (
              <button
                key={type.value}
                onClick={() => handleResourceTypeToggle(type.value)}
                className={`px-2.5 py-1 text-xs rounded-full transition-colors ${
                  filters.resourceTypes.includes(type.value)
                    ? 'bg-primary-100 text-primary-700 border border-primary-200'
                    : 'bg-gray-100 text-gray-700 border border-transparent hover:bg-gray-200'
                }`}
              >
                {type.label}
              </button>
            ))}
          </div>
        </div>

        {/* Status */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-2">Status</label>
          <select
            value={filters.status}
            onChange={(e) => handleStatusChange(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Clear Filters */}
        {(filters.projectIds.length > 0 ||
          filters.resourceTypes.length > 0 ||
          filters.status ||
          filters.search) && (
          <button
            onClick={() =>
              onFiltersChange({
                projectIds: [],
                resourceTypes: [],
                status: '',
                search: '',
                view: filters.view,
              })
            }
            className="w-full px-3 py-2 text-sm text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
          >
            Clear all filters
          </button>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <div className="text-xs text-gray-400">
          <div className="font-medium text-gray-500 mb-1">Inferred Path Warning</div>
          <p>Inferred paths represent logical topology analysis and may not reflect actual packet forwarding configuration.</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
