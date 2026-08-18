/** Compact filters for the single Traffic Topology. */
import React, { useEffect, useState } from 'react';
import type { Project, TopologyFilters } from '@/types';
import { getProjects } from '@/api/topology';

interface SidebarProps {
  filters: TopologyFilters;
  onFiltersChange: (filters: TopologyFilters) => void;
}

const RESOURCE_TYPES = [
  { value: 'server', label: 'VM' },
  { value: 'router', label: 'Router' },
  { value: 'network', label: 'Network' },
];
const ALL_RESOURCE_TYPES = RESOURCE_TYPES.map((item) => item.value);

const Sidebar: React.FC<SidebarProps> = ({ filters, onFiltersChange }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProjects()
      .then((response) => setProjects([...response.projects].sort((a, b) => a.name.localeCompare(b.name))))
      .catch((error) => console.error('Failed to load projects:', error))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!loading && projects.length > 0 && filters.projectIds.length === 0) {
      onFiltersChange({ ...filters, projectIds: [projects[0].id] });
    }
  }, [loading, projects, filters, onFiltersChange]);

  const selectedTypes = filters.resourceTypes.length > 0
    ? filters.resourceTypes
    : ALL_RESOURCE_TYPES;

  const toggleResource = (resourceType: string) => {
    const next = selectedTypes.includes(resourceType)
      ? selectedTypes.filter((value) => value !== resourceType)
      : [...selectedTypes, resourceType];
    onFiltersChange({
      ...filters,
      resourceTypes: next.length === ALL_RESOURCE_TYPES.length ? [] : next,
    });
  };

  return (
    <aside className="w-64 shrink-0 overflow-y-auto border-r border-slate-200 bg-white">
      <div className="space-y-5 p-4">
        <section>
          <label className="mb-1.5 block text-xs font-medium text-slate-600">Search</label>
          <div className="relative">
            <input
              value={filters.search}
              onChange={(event) => onFiltersChange({ ...filters, search: event.target.value })}
              placeholder="Name, IP, UUID…"
              className="w-full rounded-md border border-slate-200 py-2 pl-8 pr-3 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
            />
            <svg className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m21 21-4.35-4.35m2.35-5.65a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z" />
            </svg>
          </div>
        </section>

        <section>
          <label className="mb-1.5 block text-xs font-medium text-slate-600">Project</label>
          <select
            value={filters.projectIds[0] || ''}
            disabled={loading || projects.length === 0}
            onChange={(event) => onFiltersChange({ ...filters, projectIds: event.target.value ? [event.target.value] : [] })}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
          >
            {loading && <option value="">Loading projects…</option>}
            {!loading && projects.length === 0 && <option value="">No projects found</option>}
            {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
          </select>
        </section>

        <section>
          <div className="mb-2 text-xs font-medium text-slate-600">Resource Filter</div>
          <div className="space-y-2">
            {RESOURCE_TYPES.map((resource) => (
              <label key={resource.value} className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={selectedTypes.includes(resource.value)}
                  onChange={() => toggleResource(resource.value)}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                {resource.label}
              </label>
            ))}
          </div>
        </section>

        <section>
          <label className="mb-1.5 block text-xs font-medium text-slate-600">Status</label>
          <select
            value={filters.status}
            onChange={(event) => onFiltersChange({ ...filters, status: event.target.value })}
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
          >
            <option value="">All</option>
            <option value="ACTIVE">Active</option>
            <option value="SHUTOFF">Shutoff</option>
            <option value="ERROR">Error</option>
          </select>
        </section>

        {(filters.search || filters.status || filters.resourceTypes.length > 0) && (
          <button
            onClick={() => onFiltersChange({ ...filters, search: '', status: '', resourceTypes: [] })}
            className="text-xs font-medium text-slate-500 hover:text-slate-800"
          >
            Reset filters
          </button>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;
