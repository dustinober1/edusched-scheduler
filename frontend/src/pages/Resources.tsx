import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import ResourceDashboard from '../components/ResourceDashboard';
import {
  BuildingOfficeIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import { resourcesApi } from '../api/endpoints';
import { Resource } from '../types';

export default function Resources() {
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [dateRange] = useState({
    start: new Date(),
    end: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
  });

  // Fetch resources
  const {
    data: resources = [],
    isLoading: resourcesLoading,
    error: resourcesError,
    refetch: refetchResources,
  } = useQuery({
    queryKey: ['resources'],
    queryFn: resourcesApi.getAll,
    refetchInterval: 60000, // Refresh every minute
  });

  // Handle resource click
  const handleResourceClick = (resource: any) => {
    console.log('Resource clicked:', resource);
    // Open resource details modal or navigate to details page
  };

  // Handle error state
  if (resourcesError) {
    return (
      <div className="space-y-6">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <h3 className="text-sm font-medium text-red-800">Error Loading Resources</h3>
          <p className="text-sm text-red-700 mt-1">{(resourcesError as any)?.message || 'Unknown error'}</p>
          <button
            onClick={() => refetchResources()}
            className="mt-2 text-sm text-red-600 hover:text-red-800 font-medium"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Resources</h1>
        <p className="mt-2 text-sm text-gray-600">
          Manage classrooms, labs, equipment, and other scheduling resources
        </p>
      </div>

      {/* Actions Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-3 sm:space-y-0">
        <div className="flex items-center space-x-3">
          {/* Search */}
          <div className="relative">
            <input
              type="text"
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              placeholder="Search resources..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <MagnifyingGlassIcon className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
          </div>

          {/* Filters Toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm leading-4 font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            <FunnelIcon className="h-4 w-4 mr-2" />
            Filters
          </button>
        </div>

        {/* Add Resource Button */}
        <button
          onClick={() => {
            // Open add resource modal
            toast('Add resource feature coming soon');
          }}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          <PlusIcon className="h-4 w-4 mr-2" />
          Add Resource
        </button>
      </div>

      {/* Resource Dashboard */}
      <ResourceDashboard
        resources={resources}
        onResourceClick={handleResourceClick}
        dateRange={dateRange}
      />

      {/* Placeholder for additional content */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Resource Management</h3>
        </div>
        <div className="p-8 text-center text-gray-500">
          <BuildingOfficeIcon className="mx-auto h-12 w-12 mb-2" />
          <p>Advanced resource management features will be implemented here</p>
          <p className="text-sm mt-1">Including bulk operations, import/export, and resource analytics</p>
        </div>
      </div>
    </div>
  );
}