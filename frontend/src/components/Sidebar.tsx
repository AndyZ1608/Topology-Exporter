/** Compact project selector for the operational topology. */
import React, { useEffect, useState } from 'react';
import type { Project } from '@/types';
import { getProjects } from '@/api/topology';

interface SidebarProps {
  selectedProjectId: string;
  onProjectChange: (projectId: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ selectedProjectId, onProjectChange }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProjects()
      .then((response) => setProjects(
        [...response.projects].sort((a, b) => a.name.localeCompare(b.name)),
      ))
      .catch((error) => console.error('Failed to load projects:', error))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!loading && projects.length > 0 && !selectedProjectId) {
      onProjectChange(projects[0].id);
    }
  }, [loading, projects, selectedProjectId, onProjectChange]);

  return (
    <aside className="w-56 shrink-0 border-r border-slate-200 bg-white">
      <div className="p-4">
        <label className="mb-1.5 block text-xs font-medium text-slate-600">Project</label>
        <select
          value={selectedProjectId}
          disabled={loading || projects.length === 0}
          onChange={(event) => onProjectChange(event.target.value)}
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-800 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
        >
          {loading && <option value="">Loading projects…</option>}
          {!loading && projects.length === 0 && <option value="">No projects found</option>}
          {projects.map((project) => (
            <option key={project.id} value={project.id}>{project.name}</option>
          ))}
        </select>
      </div>
    </aside>
  );
};

export default Sidebar;
