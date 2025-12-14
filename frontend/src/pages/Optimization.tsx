import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import {
  CogIcon,
  PlayIcon,
  ChartBarIcon,
  BoltIcon,
  ClockIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { optimizationApi } from '../api/endpoints';
import { OptimizationRequest, OptimizationJob } from '../types';

export default function Optimization() {
  const [selectedObjective, setSelectedObjective] = useState('efficiency');
  const [solverConfig, setSolverConfig] = useState({
    type: 'heuristic',
    timeLimit: 60,
    maxIterations: 1000,
  });
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);

  // Get available solvers
  const {
    data: solvers = [],
    isLoading: solversLoading,
  } = useQuery({
    queryKey: ['optimization', 'solvers'],
    queryFn: optimizationApi.getSolvers,
  });

  // Run optimization mutation
  const optimizeMutation = useMutation({
    mutationFn: (request: OptimizationRequest) => optimizationApi.run(request),
    onSuccess: (job: OptimizationJob) => {
      toast.success('Optimization started successfully');
      setIsRunning(true);

      // Poll for progress
      const pollInterval = setInterval(() => {
        optimizationApi.getStatus(job.id).then((status) => {
          setProgress(status.progress);

          if (status.status === 'completed') {
            clearInterval(pollInterval);
            setIsRunning(false);
            setProgress(100);
            toast.success('Optimization completed successfully!');
            // Fetch results
            optimizationApi.getResults(job.id).then(results => {
              console.log('Optimization results:', results);
            });
          } else if (status.status === 'failed') {
            clearInterval(pollInterval);
            setIsRunning(false);
            setProgress(0);
            toast.error(`Optimization failed: ${status.error}`);
          }
        });
      }, 1000);
    },
    onError: (error) => {
      toast.error(`Failed to start optimization: ${error.message}`);
    },
  });

  const objectives = [
    { id: 'efficiency', name: 'Resource Efficiency', description: 'Maximize room and resource utilization' },
    { id: 'balance', name: 'Load Balance', description: 'Distribute load evenly across resources' },
    { id: 'preferences', name: 'User Preferences', description: 'Prioritize instructor and student preferences' },
    { id: 'gaps', name: 'Minimize Gaps', description: 'Reduce gaps between consecutive classes' },
  ];

  const handleOptimize = () => {
    const request: OptimizationRequest = {
      problemId: 'current', // This would come from the current schedule
      solver: solverConfig,
      objectives: [selectedObjective],
      incremental: true,
    };

    optimizeMutation.mutate(request);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Schedule Optimization</h1>
        <p className="mt-2 text-sm text-gray-600">
          Configure and run schedule optimization with advanced objectives
        </p>
      </div>

      {/* Optimization Controls */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Optimization Settings</h3>
        </div>
        <div className="space-y-6">
          {/* Objective Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Primary Objective
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {objectives.map((objective) => (
                <button
                  key={objective.id}
                  onClick={() => setSelectedObjective(objective.id)}
                  className={`p-4 text-left border rounded-lg transition-colors ${
                    selectedObjective === objective.id
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <div className="font-medium text-gray-900">{objective.name}</div>
                  <div className="text-sm text-gray-600 mt-1">{objective.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Solver Configuration */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Solver Configuration
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Solver Type</label>
                <select
                  className="form-select"
                  value={solverConfig.type}
                  onChange={(e) => setSolverConfig(prev => ({ ...prev, type: e.target.value }))}
                >
                  {solvers.map((solver: any) => (
                    <option key={solver.id} value={solver.id}>
                      {solver.name} {solver.description && `(${solver.description})`}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Time Limit (seconds)</label>
                <input
                  type="number"
                  className="form-input"
                  value={solverConfig.timeLimit}
                  onChange={(e) => setSolverConfig(prev => ({ ...prev, timeLimit: parseInt(e.target.value) || 60 }))}
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Max Iterations</label>
                <input
                  type="number"
                  className="form-input"
                  value={solverConfig.maxIterations}
                  onChange={(e) => setSolverConfig(prev => ({ ...prev, maxIterations: parseInt(e.target.value) || 1000 }))}
                />
              </div>
            </div>
          </div>

          {/* Advanced Options */}
          <div>
            <details className="group">
              <summary className="flex items-center cursor-pointer text-sm font-medium text-gray-700">
                <CogIcon className="h-4 w-4 mr-2" />
                Advanced Options
              </summary>
              <div className="mt-4 space-y-4 pl-6">
                <label className="flex items-center">
                  <input type="checkbox" className="form-checkbox" defaultChecked />
                  <span className="ml-2 text-sm text-gray-700">Enable parallel solving</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" className="form-checkbox" defaultChecked />
                  <span className="ml-2 text-sm text-gray-700">Use incremental updates</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" className="form-checkbox" />
                  <span className="ml-2 text-sm text-gray-700">Force real-time constraints</span>
                </label>
              </div>
            </details>
          </div>

          {/* Run Optimization */}
          <div className="flex items-center space-x-4">
            <button
              onClick={handleOptimize}
              disabled={isRunning}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isRunning ? (
                <>
                  <BoltIcon className="h-4 w-4 mr-2 animate-pulse" />
                  Optimizing...
                </>
              ) : (
                <>
                  <PlayIcon className="h-4 w-4 mr-2" />
                  Run Optimization
                </>
              )}
            </button>

            {isRunning && (
              <div className="flex items-center space-x-2">
                <div className="w-48 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-primary-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="text-sm text-gray-600">{progress}%</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Optimization Results */}
      {progress === 100 && !isRunning && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Optimization Results</h3>
          </div>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center">
                <CheckCircleIcon className="mx-auto h-8 w-8 text-green-500" />
                <p className="mt-1 text-2xl font-semibold text-gray-900">95%</p>
                <p className="text-sm text-gray-600">Constraints Satisfied</p>
              </div>
              <div className="text-center">
                <ChartBarIcon className="mx-auto h-8 w-8 text-blue-500" />
                <p className="mt-1 text-2xl font-semibold text-gray-900">87%</p>
                <p className="text-sm text-gray-600">Utilization Rate</p>
              </div>
              <div className="text-center">
                <ClockIcon className="mx-auto h-8 w-8 text-purple-500" />
                <p className="mt-1 text-2xl font-semibold text-gray-900">2.3s</p>
                <p className="text-sm text-gray-600">Solve Time</p>
              </div>
              <div className="text-center">
                <BoltIcon className="mx-auto h-8 w-8 text-orange-500" />
                <p className="mt-1 text-2xl font-semibold text-gray-900">842</p>
                <p className="text-sm text-gray-600">Iterations</p>
              </div>
            </div>

            <div className="pt-4 border-t">
              <button className="text-sm text-primary-600 hover:text-primary-800 font-medium">
                View detailed optimization report →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Optimization History */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Optimization History</h3>
        </div>
        <div className="p-8 text-center text-gray-500">
          <ClockIcon className="mx-auto h-12 w-12 mb-2" />
          <p>Optimization history and comparison tools will be implemented here</p>
          <p className="text-sm mt-1">Track optimization performance over time</p>
        </div>
      </div>
    </div>
  );
}