import apiClient from './client';
import {
  Assignment,
  Constraint,
  Resource,
  Problem,
  Result,
  OptimizationRequest,
  Integration
} from '@/types';

// Schedules
export const schedulesApi = {
  // Get all schedules
  getAll: () => apiClient.get('/schedules').then(res => res.data),

  // Get schedule by ID
  getById: (id: string) => apiClient.get(`/schedules/${id}`).then(res => res.data),

  // Create new schedule
  create: (problem: Problem) => apiClient.post('/schedules', problem).then(res => res.data),

  // Update schedule
  update: (id: string, updates: Partial<Problem>) =>
    apiClient.put(`/schedules/${id}`, updates).then(res => res.data),

  // Delete schedule
  delete: (id: string) => apiClient.delete(`/schedules/${id}`).then(res => res.data),

  // Export schedule
  export: (id: string, format: 'json' | 'csv' | 'ical' | 'excel' | 'pdf') =>
    apiClient.get(`/schedules/${id}/export?format=${format}`, {
      responseType: 'blob'
    }).then(res => res.data),

  // Clone schedule
  clone: (id: string, name: string) =>
    apiClient.post(`/schedules/${id}/clone`, { name }).then(res => res.data),
};

// Assignments
export const assignmentsApi = {
  // Get assignments for a schedule
  getByScheduleId: (scheduleId: string) =>
    apiClient.get(`/schedules/${scheduleId}/assignments`).then(res => res.data),

  // Create assignment
  create: (scheduleId: string, assignment: Assignment) =>
    apiClient.post(`/schedules/${scheduleId}/assignments`, assignment).then(res => res.data),

  // Update assignment
  update: (scheduleId: string, assignmentId: string, updates: Partial<Assignment>) =>
    apiClient.put(`/schedules/${scheduleId}/assignments/${assignmentId}`, updates).then(res => res.data),

  // Delete assignment
  delete: (scheduleId: string, assignmentId: string) =>
    apiClient.delete(`/schedules/${scheduleId}/assignments/${assignmentId}`).then(res => res.data),

  // Move assignment (drag and drop)
  move: (scheduleId: string, assignmentId: string, newTime: string, newResourceId?: string) =>
    apiClient.post(`/schedules/${scheduleId}/assignments/${assignmentId}/move`, {
      newTime,
      newResourceId
    }).then(res => res.data),
};

// Resources
export const resourcesApi = {
  // Get all resources
  getAll: () => apiClient.get('/resources').then(res => res.data),

  // Get resource by ID
  getById: (id: string) => apiClient.get(`/resources/${id}`).then(res => res.data),

  // Create resource
  create: (resource: Omit<Resource, 'id'>) =>
    apiClient.post('/resources', resource).then(res => res.data),

  // Update resource
  update: (id: string, updates: Partial<Resource>) =>
    apiClient.put(`/resources/${id}`, updates).then(res => res.data),

  // Delete resource
  delete: (id: string) => apiClient.delete(`/resources/${id}`).then(res => res.data),

  // Get resource availability
  getAvailability: (id: string, startDate: string, endDate: string) =>
    apiClient.get(`/resources/${id}/availability`, {
      params: { startDate, endDate }
    }).then(res => res.data),

  // Get utilization metrics
  getUtilization: (id?: string, startDate?: string, endDate?: string) =>
    apiClient.get('/resources/utilization', {
      params: { resourceId: id, startDate, endDate }
    }).then(res => res.data),

  // Bulk import resources
  bulkImport: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/resources/bulk-import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(res => res.data);
  },
};

// Constraints
export const constraintsApi = {
  // Get all constraints
  getAll: () => apiClient.get('/constraints').then(res => res.data),

  // Get constraint by ID
  getById: (id: string) => apiClient.get(`/constraints/${id}`).then(res => res.data),

  // Create constraint
  create: (constraint: Omit<Constraint, 'id'>) =>
    apiClient.post('/constraints', constraint).then(res => res.data),

  // Update constraint
  update: (id: string, updates: Partial<Constraint>) =>
    apiClient.put(`/constraints/${id}`, updates).then(res => res.data),

  // Delete constraint
  delete: (id: string) => apiClient.delete(`/constraints/${id}`).then(res => res.data),

  // Toggle constraint enabled/disabled
  toggle: (id: string) => apiClient.post(`/constraints/${id}/toggle`).then(res => res.data),

  // Validate constraints
  validate: (constraints: Constraint[]) =>
    apiClient.post('/constraints/validate', { constraints }).then(res => res.data),

  // Get constraint templates
  getTemplates: () => apiClient.get('/constraints/templates').then(res => res.data),
};

// Optimization
export const optimizationApi = {
  // Run optimization
  run: (request: OptimizationRequest) =>
    apiClient.post('/optimization/run', request).then(res => res.data),

  // Get optimization status
  getStatus: (jobId: string) =>
    apiClient.get(`/optimization/status/${jobId}`).then(res => res.data),

  // Get optimization results
  getResults: (jobId: string) =>
    apiClient.get(`/optimization/results/${jobId}`).then(res => res.data),

  // Cancel optimization
  cancel: (jobId: string) =>
    apiClient.post(`/optimization/cancel/${jobId}`).then(res => res.data),

  // Get available solvers
  getSolvers: () => apiClient.get('/optimization/solvers').then(res => res.data),

  // Get optimization history
  getHistory: () => apiClient.get('/optimization/history').then(res => res.data),
};

// Integrations
export const integrationsApi = {
  // Get all integrations
  getAll: () => apiClient.get('/integrations').then(res => res.data),

  // Get integration by type
  getByType: (type: string) => apiClient.get(`/integrations/${type}`).then(res => res.data),

  // Configure integration
  configure: (type: string, config: any) =>
    apiClient.post(`/integrations/${type}/configure`, config).then(res => res.data),

  // Test connection
  test: (type: string) => apiClient.post(`/integrations/${type}/test`).then(res => res.data),

  // Sync data
  sync: (type: string, options?: any) =>
    apiClient.post(`/integrations/${type}/sync`, options).then(res => res.data),

  // Disconnect integration
  disconnect: (type: string) =>
    apiClient.post(`/integrations/${type}/disconnect`).then(res => res.data),
};

// Analytics
export const analyticsApi = {
  // Get dashboard stats
  getDashboardStats: () => apiClient.get('/analytics/dashboard').then(res => res.data),

  // Get utilization report
  getUtilizationReport: (params: any) =>
    apiClient.get('/analytics/utilization', { params }).then(res => res.data),

  // Get conflict analysis
  getConflictAnalysis: (scheduleId: string) =>
    apiClient.get(`/analytics/conflicts/${scheduleId}`).then(res => res.data),

  // Get performance metrics
  getPerformanceMetrics: (params: any) =>
    apiClient.get('/analytics/performance', { params }).then(res => res.data),

  // Export analytics
  export: (type: string, params: any) =>
    apiClient.get(`/analytics/export/${type}`, {
      params,
      responseType: 'blob'
    }).then(res => res.data),
};

// System
export const systemApi = {
  // Get system health
  getHealth: () => apiClient.get('/system/health').then(res => res.data),

  // Get system info
  getInfo: () => apiClient.get('/system/info').then(res => res.data),

  // Get system configuration
  getConfig: () => apiClient.get('/system/config').then(res => res.data),

  // Update system configuration
  updateConfig: (config: any) =>
    apiClient.put('/system/config', config).then(res => res.data),
};