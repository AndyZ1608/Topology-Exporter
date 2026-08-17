/**
 * API service for topology data.
 */
import axios from 'axios';
import type {
  TopologyResponse,
  InternetPathResponse,
  SyncStatus,
  ProjectsResponse,
  TopologyFilters,
} from '@/types';

const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Health check
 */
export async function getHealth(): Promise<{ status: string; demo_mode: boolean }> {
  const response = await api.get('/health');
  return response.data;
}

/**
 * Get sync status
 */
export async function getSyncStatus(): Promise<SyncStatus> {
  const response = await api.get('/sync/status');
  return response.data;
}

/**
 * Trigger topology refresh
 */
export async function refreshTopology(): Promise<SyncStatus> {
  const response = await api.post('/sync/refresh');
  return response.data;
}

/**
 * Get topology with filters
 */
export async function getTopology(filters?: Partial<TopologyFilters>): Promise<TopologyResponse> {
  const params = new URLSearchParams();

  if (filters?.projectIds?.length) {
    params.append('project_id', filters.projectIds.join(','));
  }
  if (filters?.resourceTypes?.length) {
    params.append('resource_type', filters.resourceTypes.join(','));
  }
  if (filters?.status) {
    params.append('status', filters.status);
  }
  if (filters?.search) {
    params.append('search', filters.search);
  }
  if (filters?.view) {
    params.append('view', filters.view);
  }

  const response = await api.get('/topology', { params });
  return response.data;
}

/**
 * Get full topology without filters
 */
export async function getFullTopology(): Promise<TopologyResponse> {
  const response = await api.get('/topology/full');
  return response.data;
}

/**
 * Get topology summary
 */
export async function getTopologySummary(): Promise<Record<string, unknown>> {
  const response = await api.get('/topology/summary');
  return response.data;
}

/**
 * Get list of projects
 */
export async function getProjects(): Promise<ProjectsResponse> {
  const response = await api.get('/projects');
  return response.data;
}

/**
 * Get a specific project
 */
export async function getProject(projectId: string): Promise<Record<string, unknown>> {
  const response = await api.get(`/projects/${projectId}`);
  return response.data;
}

/**
 * Get node details
 */
export async function getNode(nodeId: string): Promise<Record<string, unknown>> {
  const response = await api.get(`/nodes/${encodeURIComponent(nodeId)}`);
  return response.data;
}

/**
 * Get node connections
 */
export async function getNodeConnections(nodeId: string): Promise<Record<string, unknown>> {
  const response = await api.get(`/nodes/${encodeURIComponent(nodeId)}/connections`);
  return response.data;
}

/**
 * Get internet path for a server
 */
export async function getInternetPath(serverId: string): Promise<InternetPathResponse> {
  const response = await api.get(`/path/${encodeURIComponent(serverId)}/internet`);
  return response.data;
}

/**
 * Get all paths from a server
 */
export async function getAllPaths(serverId: string): Promise<Record<string, unknown>> {
  const response = await api.get(`/path/${encodeURIComponent(serverId)}/paths`);
  return response.data;
}

export default api;
