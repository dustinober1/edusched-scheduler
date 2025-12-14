import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import ScheduleCalendar from '../components/ScheduleCalendar';
import ConstraintBuilder from '../components/ConstraintBuilder';
import {
  PlusIcon,
  SaveIcon,
  PlayIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { schedulesApi, assignmentsApi, optimizationApi } from '../api/endpoints';
import { Assignment, Problem, Constraint, OptimizationRequest } from '../types';

export default function ScheduleEditor() {
  const navigate = useNavigate();
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'schedule' | 'constraints' | 'optimization'>('schedule');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Fetch schedule/problem data
  const {
    data: problem,
    isLoading: problemLoading,
    error: problemError,
  } = useQuery({
    queryKey: ['schedule', id],
    queryFn: () => id ? schedulesApi.getById(id) : null,
    enabled: !!id,
  });

  // Fetch assignments
  const {
    data: assignments = [],
    isLoading: assignmentsLoading,
    error: assignmentsError,
  } = useQuery({
    queryKey: ['assignments', id],
    queryFn: () => id ? assignmentsApi.getByScheduleId(id) : [],
    enabled: !!id,
  });

  // Create new schedule mutation
  const createScheduleMutation = useMutation({
    mutationFn: schedulesApi.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
      navigate(`/schedule/editor/${data.id}`);
      toast.success('Schedule created successfully');
    },
    onError: (error) => {
      toast.error(`Failed to create schedule: ${error.message}`);
    },
  });

  // Update assignment mutation
  const updateAssignmentMutation = useMutation({
    mutationFn: ({ assignmentId, updates }: { assignmentId: string; updates: Partial<Assignment> }) =>
      id ? assignmentsApi.update(id, assignmentId, updates) : Promise.reject('No schedule ID'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments', id] });
      toast.success('Assignment updated');
    },
    onError: (error) => {
      toast.error(`Failed to update assignment: ${error.message}`);
    },
  });

  // Delete assignment mutation
  const deleteAssignmentMutation = useMutation({
    mutationFn: (assignmentId: string) =>
      id ? assignmentsApi.delete(id, assignmentId) : Promise.reject('No schedule ID'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments', id] });
      toast.success('Assignment deleted');
    },
    onError: (error) => {
      toast.error(`Failed to delete assignment: ${error.message}`);
    },
  });

  // Move assignment mutation (drag and drop)
  const moveAssignmentMutation = useMutation({
    mutationFn: ({ assignmentId, newTime, newResourceId }: {
      assignmentId: string;
      newTime: string;
      newResourceId?: string;
    }) => id ? assignmentsApi.move(id, assignmentId, newTime, newResourceId) : Promise.reject('No schedule ID'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments', id] });
      toast.success('Assignment moved');
    },
    onError: (error) => {
      toast.error(`Failed to move assignment: ${error.message}`);
    },
  });

  // Run optimization mutation
  const optimizeMutation = useMutation({
    mutationFn: (request: OptimizationRequest) => optimizationApi.run(request),
    onSuccess: (job) => {
      toast.success('Optimization started');
      // Poll for results
      const pollInterval = setInterval(() => {
        optimizationApi.getStatus(job.id).then((status) => {
          if (status.status === 'completed') {
            clearInterval(pollInterval);
            queryClient.invalidateQueries({ queryKey: ['assignments', id] });
            toast.success('Optimization completed');
          } else if (status.status === 'failed') {
            clearInterval(pollInterval);
            toast.error(`Optimization failed: ${status.error}`);
          }
        });
      }, 1000);
    },
    onError: (error) => {
      toast.error(`Failed to start optimization: ${error.message}`);
    },
  });

  // Handle assignment click
  const handleAssignmentClick = (assignment: Assignment) => {
    // Open assignment details modal or navigate to details page
    console.log('Assignment clicked:', assignment);
  };

  // Handle date selection (create new assignment)
  const handleDateSelect = (dateInfo: any) => {
    if (!id) return;

    const newAssignment: Partial<Assignment> = {
      startTime: dateInfo.start,
      endTime: dateInfo.end,
      resourceId: dateInfo.resource?.id,
      // Prompt user for session details
    };

    console.log('Create assignment for:', newAssignment);
    // Open modal to collect session details
  };

  // Handle assignment drop (move)
  const handleAssignmentDrop = (assignmentId: string, newTime: Date, resourceId?: string) => {
    moveAssignmentMutation.mutate({
      assignmentId,
      newTime: newTime.toISOString(),
      newResourceId,
    });
  };

  // Handle optimization
  const handleOptimize = () => {
    if (!id) return;

    const request: OptimizationRequest = {
      problemId: id,
      solver: {
        type: 'heuristic',
        config: { timeLimit: 60 },
        timeLimit: 60,
      },
      objectives: ['efficiency', 'balance'],
    };

    optimizeMutation.mutate(request);
  };

  // Create new schedule if none exists
  useEffect(() => {
    if (!id && !problemLoading) {
      const newProblem: Problem = {
        id: '', // Will be set by server
        name: 'New Schedule',
        dateRange: {
          start: new Date(),
          end: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000), // 90 days
        },
        timeSlots: [],
        requests: [],
        resources: [],
        constraints: [],
        objectives: [],
      };

      createScheduleMutation.mutate(newProblem);
    }
  }, [id, problemLoading]);

  if (problemLoading || assignmentsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (problemError || assignmentsError) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <h3 className="text-sm font-medium text-red-800">Error Loading Schedule</h3>
        <p className="text-sm text-red-700 mt-1">
          {problemError?.message || assignmentsError?.message}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {problem?.name || 'New Schedule'}
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Create and edit your course schedule
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={handleOptimize}
            disabled={optimizeMutation.isLoading || !id}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {optimizeMutation.isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Optimizing...
              </>
            ) : (
              <>
                <PlayIcon className="h-4 w-4 mr-2" />
                Run Optimization
              </>
            )}
          </button>
          <button className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
            <SaveIcon className="h-4 w-4 mr-2" />
            Save
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('schedule')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'schedule'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Schedule View
          </button>
          <button
            onClick={() => setActiveTab('constraints')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'constraints'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Constraints
          </button>
          <button
            onClick={() => setActiveTab('optimization')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'optimization'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Optimization
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'schedule' && (
        <div>
          {/* Conflict Warning */}
          {assignments.some((a) => a.conflicts && a.conflicts.length > 0) && (
            <div className="mb-4 bg-yellow-50 border border-yellow-200 rounded-md p-4">
              <div className="flex">
                <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-yellow-800">
                    {assignments.filter((a) => a.conflicts?.length).length} conflicts detected
                  </h3>
                  <p className="text-sm text-yellow-700 mt-1">
                    Some assignments have conflicts. Review the Constraints tab to resolve them.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Calendar */}
          <ScheduleCalendar
            assignments={assignments}
            onAssignmentClick={handleAssignmentClick}
            onDateSelect={handleDateSelect}
            onAssignmentDrop={handleAssignmentDrop}
            editable={true}
            view="timeGridWeek"
          />
        </div>
      )}

      {activeTab === 'constraints' && (
        <ConstraintBuilder
          constraints={problem?.constraints || []}
          onAdd={(constraint) => {
            // Add constraint to problem
            console.log('Add constraint:', constraint);
          }}
          onUpdate={(id, updates) => {
            // Update constraint
            console.log('Update constraint:', id, updates);
          }}
          onDelete={(id) => {
            // Delete constraint
            console.log('Delete constraint:', id);
          }}
          onToggle={(id) => {
            // Toggle constraint
            console.log('Toggle constraint:', id);
          }}
        />
      )}

      {activeTab === 'optimization' && (
        <div className="space-y-6">
          {/* Optimization Status */}
          {optimizeMutation.isLoading && (
            <div className="card">
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600 mr-3"></div>
                <div>
                  <p className="text-sm font-medium text-gray-900">Optimization in Progress</p>
                  <p className="text-sm text-gray-600">Finding the best schedule...</p>
                </div>
              </div>
            </div>
          )}

          {/* Optimization Settings */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Optimization Settings</h3>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Solver Type
                </label>
                <select className="form-select">
                  <option>Heuristic (Fast)</option>
                  <option>OR-Tools CP-SAT (Optimal)</option>
                  <option>Hybrid (Balanced)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Time Limit (seconds)
                </label>
                <input type="number" className="form-input" defaultValue="60" />
              </div>
              <button
                onClick={handleOptimize}
                disabled={optimizeMutation.isLoading || !id}
                className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {optimizeMutation.isLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Optimizing...
                  </>
                ) : (
                  <>
                    <PlayIcon className="h-4 w-4 mr-2" />
                    Run Optimization
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Optimization History */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Recent Optimizations</h3>
            </div>
            <div className="p-8 text-center text-gray-500">
              <DocumentTextIcon className="mx-auto h-12 w-12 mb-2" />
              <p>Optimization history will appear here</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}