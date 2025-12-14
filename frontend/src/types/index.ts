// Domain Types
export interface SessionRequest {
  id: string;
  name: string;
  courseCode: string;
  duration: number; // minutes
  occurrences: number;
  dateRange: {
    start: Date;
    end: Date;
  };
  requirements: {
    roomType?: string;
    capacity?: number;
    equipment?: string[];
    features?: string[];
  };
  preferences?: {
    timeSlots?: string[];
    rooms?: string[];
    buildings?: string[];
  };
  instructor?: string;
  department?: string;
  campus?: string;
  priority?: number;
}

export interface Resource {
  id: string;
  name: string;
  type: 'room' | 'lab' | 'lecture_hall' | 'computer_lab' | 'equipment';
  building: string;
  campus: string;
  capacity?: number;
  features: string[];
  availability: {
    [date: string]: {
      [time: string]: boolean;
    };
  };
  utilization: number;
  scheduleCount: number;
  location?: {
    floor?: string;
    coordinates?: {
      lat: number;
      lng: number;
    };
  };
  equipment?: string[];
  cost?: {
    perHour: number;
    currency: string;
  };
}

export interface Constraint {
  id: string;
  name: string;
  type: 'hard' | 'soft';
  category: string;
  enabled: boolean;
  parameters: Record<string, any>;
  priority?: number;
  weight?: number;
  description?: string;
}

export interface Assignment {
  id: string;
  sessionId: string;
  resourceId: string;
  startTime: Date;
  endTime: Date;
  resource: Resource;
  session: SessionRequest;
  conflicts?: string[];
  score?: number;
  metadata?: {
    created: Date;
    modified: Date;
    createdBy: string;
  };
}

export interface Problem {
  id: string;
  name: string;
  description?: string;
  semester?: string;
  dateRange: {
    start: Date;
    end: Date;
  };
  timeSlots: string[];
  requests: SessionRequest[];
  resources: Resource[];
  constraints: Constraint[];
  objectives: OptimizationObjective[];
  metadata?: {
    created: Date;
    modified: Date;
    version: number;
  };
}

export interface Result {
  id: string;
  problemId: string;
  assignments: Assignment[];
  statistics: {
    totalAssignments: number;
    constraintViolations: number;
    utilizationRate: number;
    score: number;
    solveTime: number;
    iterations: number;
  };
  solver: {
    type: string;
    version: string;
    config: Record<string, any>;
  };
  timestamp: Date;
  status: 'success' | 'error' | 'partial';
  message?: string;
}

export interface OptimizationObjective {
  id: string;
  name: string;
  type: string;
  weight: number;
  parameters: Record<string, any>;
  enabled: boolean;
}

// API Types
export interface DashboardStats {
  totalCourses: number;
  totalAssignments: number;
  conflictCount: number;
  utilizationRate: number;
  nextSchedules: number;
  activeOptimizations: number;
}

export interface OptimizationRequest {
  problemId: string;
  solver: {
    type: string;
    config: Record<string, any>;
    timeLimit?: number;
    maxIterations?: number;
  };
  objectives: string[];
  incremental?: boolean;
  seed?: number;
}

export interface OptimizationJob {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  startedAt: Date;
  completedAt?: Date;
  request: OptimizationRequest;
  result?: Result;
  error?: string;
  logs?: string[];
}

export interface Integration {
  id: string;
  name: string;
  type: 'sis' | 'calendar' | 'notification' | 'other';
  description: string;
  status: 'connected' | 'disconnected' | 'error';
  lastSync?: Date;
  config?: Record<string, any>;
  capabilities: string[];
  metrics?: {
    syncCount: number;
    lastSyncDuration: number;
    errors: number;
  };
}

export interface ActivityLog {
  id: string;
  type: string;
  message: string;
  timestamp: Date;
  userId?: string;
  details?: Record<string, any>;
  severity: 'info' | 'warning' | 'error';
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'scheduler' | 'viewer';
  preferences: {
    theme: 'light' | 'dark' | 'system';
    timezone: string;
    defaultView: string;
    notifications: Record<string, boolean>;
  };
  lastLogin?: Date;
  permissions: string[];
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  severity: 'info' | 'success' | 'warning' | 'error';
  timestamp: Date;
  read: boolean;
  userId: string;
  actionUrl?: string;
  metadata?: Record<string, any>;
}

export interface Conflict {
  id: string;
  type: string;
  severity: 'high' | 'medium' | 'low';
  description: string;
  assignments: string[]; // Assignment IDs
  constraint?: string; // Constraint ID
  suggestions?: ConflictSuggestion[];
  autoResolve?: boolean;
}

export interface ConflictSuggestion {
  description: string;
  action: string;
  parameters: Record<string, any>;
  impact: {
    assignmentsAffected: number;
    scoreChange: number;
  };
}

export interface ExportOptions {
  format: 'json' | 'csv' | 'ical' | 'excel' | 'pdf';
  includeDetails?: boolean;
  dateRange?: {
    start: Date;
    end: Date;
  };
  resources?: string[];
  departments?: string[];
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'down';
  version: string;
  uptime: number;
  checks: {
    database: boolean;
    solver: boolean;
    storage: boolean;
    integrations: boolean;
  };
  metrics: {
    activeConnections: number;
    requestsPerSecond: number;
    memoryUsage: number;
    cpuUsage: number;
  };
}

// Component Props Types
export interface ScheduleCalendarProps {
  assignments: Assignment[];
  onAssignmentClick?: (assignment: Assignment) => void;
  onDateSelect?: (date: Date, resourceId?: string) => void;
  onAssignmentDrop?: (assignmentId: string, newTime: Date, resourceId?: string) => void;
  editable?: boolean;
  view?: string;
  resources?: Resource[];
  height?: string;
}

export interface ConstraintBuilderProps {
  constraints: Constraint[];
  onAdd: (constraint: Omit<Constraint, 'id'>) => void;
  onUpdate: (id: string, updates: Partial<Constraint>) => void;
  onDelete: (id: string) => void;
  onToggle: (id: string) => void;
}

export interface ResourceDashboardProps {
  resources: Resource[];
  onResourceClick?: (resource: Resource) => void;
  dateRange: {
    start: Date;
    end: Date;
  };
}

// WebSocket Message Types
export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

export type WSMessageType =
  | 'schedule_update'
  | 'assignment_created'
  | 'assignment_updated'
  | 'assignment_deleted'
  | 'resource_update'
  | 'constraint_update'
  | 'optimization_started'
  | 'optimization_progress'
  | 'optimization_complete'
  | 'conflict_detected'
  | 'conflict_resolved'
  | 'system_notification'
  | 'user_activity';

// API Schedule Types (matches backend response)
export interface Schedule {
  id: string;
  name?: string;
  status: string;
  total_assignments: number;
  solver_time_ms: number;
  iterations?: number;
  assignments: ScheduleAssignment[];
  created_at?: string;
  updated_at?: string;
  metadata?: Record<string, any>;
  solver_config?: Record<string, any>;
}

export interface ScheduleAssignment {
  request_id: string;
  resource_id: string;
  start_time: string;
  end_time: string;
  course_code?: string;
  teacher_name?: string;
  room_name?: string;
  building_id?: string;
  enrollment?: number;
  capacity?: number;
}