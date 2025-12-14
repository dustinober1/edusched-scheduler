import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import ConstraintBuilder from '../components/ConstraintBuilder';
import {
  ShieldCheckIcon,
  PlusIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { constraintsApi, analyticsApi } from '../api/endpoints';
import { Constraint } from '../types';

export default function Constraints() {
  const [activeTab, setActiveTab] = useState<'builder' | 'validation' | 'conflicts'>('builder');
  const queryClient = useQueryClient();

  // Fetch constraints
  const {
    data: constraints = [],
    isLoading: constraintsLoading,
    error: constraintsError,
  } = useQuery({
    queryKey: ['constraints'],
    queryFn: constraintsApi.getAll,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Add constraint mutation
  const addConstraintMutation = useMutation({
    mutationFn: constraintsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['constraints'] });
      toast.success('Constraint added');
    },
    onError: (error) => {
      toast.error(`Failed to add constraint: ${error.message}`);
    },
  });

  // Update constraint mutation
  const updateConstraintMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: Partial<Constraint> }) =>
      constraintsApi.update(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['constraints'] });
      toast.success('Constraint updated');
    },
    onError: (error) => {
      toast.error(`Failed to update constraint: ${error.message}`);
    },
  });

  // Delete constraint mutation
  const deleteConstraintMutation = useMutation({
    mutationFn: constraintsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['constraints'] });
      toast.success('Constraint deleted');
    },
    onError: (error) => {
      toast.error(`Failed to delete constraint: ${error.message}`);
    },
  });

  // Toggle constraint mutation
  const toggleConstraintMutation = useMutation({
    mutationFn: constraintsApi.toggle,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['constraints'] });
      toast.success('Constraint toggled');
    },
    onError: (error) => {
      toast.error(`Failed to toggle constraint: ${error.message}`);
    },
  });

  const tabs = [
    { id: 'builder', name: 'Constraint Builder', icon: PlusIcon },
    { id: 'validation', name: 'Validation Rules', icon: ShieldCheckIcon },
    { id: 'conflicts', name: 'Conflict Analysis', icon: ExclamationTriangleIcon },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Constraints</h1>
        <p className="mt-2 text-sm text-gray-600">
          Define and manage scheduling constraints and validation rules
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <tab.icon className="mr-2 h-5 w-5" />
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'builder' && (
        <ConstraintBuilder
          constraints={constraints}
          onAdd={(constraint) => addConstraintMutation.mutate(constraint)}
          onUpdate={(id, updates) => updateConstraintMutation.mutate({ id, updates })}
          onDelete={(id) => deleteConstraintMutation.mutate(id)}
          onToggle={(id) => toggleConstraintMutation.mutate(id)}
        />
      )}

      {activeTab === 'validation' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Validation Rules</h3>
            <p className="text-sm text-gray-600">
              Configure how constraints are validated and enforced
            </p>
          </div>
          <div className="p-8 text-center text-gray-500">
            <ShieldCheckIcon className="mx-auto h-12 w-12 mb-2" />
            <p>Validation rule configuration will be implemented here</p>
            <p className="text-sm mt-1">Including custom validation logic and rule priorities</p>
          </div>
        </div>
      )}

      {activeTab === 'conflicts' && (
        <div className="space-y-6">
          {/* Conflict Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card">
              <div className="flex items-center">
                <ExclamationTriangleIcon className="h-8 w-8 text-red-500" />
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-600">Active Conflicts</p>
                  <p className="text-2xl font-semibold text-gray-900">12</p>
                </div>
              </div>
            </div>
            <div className="card">
              <div className="flex items-center">
                <DocumentTextIcon className="h-8 w-8 text-yellow-500" />
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-600">Warnings</p>
                  <p className="text-2xl font-semibold text-gray-900">8</p>
                </div>
              </div>
            </div>
            <div className="card">
              <div className="flex items-center">
                <ShieldCheckIcon className="h-8 w-8 text-green-500" />
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-600">Resolved</p>
                  <p className="text-2xl font-semibold text-gray-900">45</p>
                </div>
              </div>
            </div>
          </div>

          {/* Conflict List */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Conflict Analysis</h3>
            </div>
            <div className="p-8 text-center text-gray-500">
              <ExclamationTriangleIcon className="mx-auto h-12 w-12 mb-2" />
              <p>Conflict detection and resolution tools will be implemented here</p>
              <p className="text-sm mt-1">Including automated suggestions and manual resolution options</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}