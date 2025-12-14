import React, { useState, useMemo } from 'react';
import {
  BuildingOfficeIcon,
  UsersIcon,
  ClockIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

interface Resource {
  id: string;
  name: string;
  type: 'room' | 'lab' | 'lecture_hall' | 'computer_lab';
  building: string;
  capacity: number;
  features: string[];
  availability: {
    [date: string]: {
      [time: string]: boolean;
    };
  };
  utilization: number;
  scheduleCount: number;
}

interface ResourceDashboardProps {
  resources: Resource[];
  onResourceClick?: (resource: Resource) => void;
  dateRange: {
    start: Date;
    end: Date;
  };
}

export default function ResourceDashboard({
  resources,
  onResourceClick,
  dateRange,
}: ResourceDashboardProps) {
  const [selectedType, setSelectedType] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'name' | 'capacity' | 'utilization'>('name');

  const resourceTypes = [
    { value: 'all', label: 'All Resources' },
    { value: 'room', label: 'Classrooms' },
    { value: 'lab', label: 'Labs' },
    { value: 'lecture_hall', label: 'Lecture Halls' },
    { value: 'computer_lab', label: 'Computer Labs' },
  ];

  const filteredAndSortedResources = useMemo(() => {
    let filtered = resources;

    // Filter by type
    if (selectedType !== 'all') {
      filtered = resources.filter(r => r.type === selectedType);
    }

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'capacity':
          return b.capacity - a.capacity;
        case 'utilization':
          return b.utilization - a.utilization;
        default:
          return 0;
      }
    });

    return filtered;
  }, [resources, selectedType, sortBy]);

  const stats = useMemo(() => {
    const totalResources = resources.length;
    const avgUtilization = resources.reduce((sum, r) => sum + r.utilization, 0) / totalResources;
    const totalCapacity = resources.reduce((sum, r) => sum + r.capacity, 0);
    const avgCapacity = totalCapacity / totalResources;

    const utilizationByType = resourceTypes.slice(1).reduce((acc, type) => {
      const typeResources = resources.filter(r => r.type === type.value);
      if (typeResources.length > 0) {
        acc[type.value] = {
          count: typeResources.length,
          utilization: typeResources.reduce((sum, r) => sum + r.utilization, 0) / typeResources.length,
          capacity: typeResources.reduce((sum, r) => sum + r.capacity, 0),
        };
      }
      return acc;
    }, {} as Record<string, any>);

    return {
      totalResources,
      avgUtilization: Math.round(avgUtilization * 100),
      avgCapacity: Math.round(avgCapacity),
      utilizationByType,
    };
  }, [resources]);

  const getUtilizationColor = (utilization: number) => {
    if (utilization >= 90) return 'text-red-600 bg-red-100';
    if (utilization >= 70) return 'text-yellow-600 bg-yellow-100';
    return 'text-green-600 bg-green-100';
  };

  const getUtilizationIcon = (utilization: number) => {
    if (utilization >= 90) {
      return <ExclamationTriangleIcon className="h-5 w-5" />;
    }
    if (utilization >= 70) {
      return <ClockIcon className="h-5 w-5" />;
    }
    return <CheckCircleIcon className="h-5 w-5" />;
  };

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center">
            <BuildingOfficeIcon className="h-8 w-8 text-gray-400" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Total Resources</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.totalResources}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <ChartBarIcon className="h-8 w-8 text-gray-400" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Avg Utilization</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.avgUtilization}%</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <UsersIcon className="h-8 w-8 text-gray-400" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Avg Capacity</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.avgCapacity}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <ClockIcon className="h-8 w-8 text-gray-400" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Scheduled Sessions</p>
              <p className="text-2xl font-semibold text-gray-900">
                {resources.reduce((sum, r) => sum + r.scheduleCount, 0)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Utilization by Type */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Utilization by Resource Type</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {Object.entries(stats.utilizationByType).map(([type, data]) => (
            <div key={type} className="text-center">
              <h4 className="text-sm font-medium text-gray-600 capitalize">
                {type.replace('_', ' ')}
              </h4>
              <p className="text-xs text-gray-500 mt-1">
                {data.count} resources • {Math.round(data.capacity / data.count)} avg capacity
              </p>
              <div className={`mt-2 inline-flex items-center px-3 py-1 rounded-full text-sm ${getUtilizationColor(data.utilization)}`}>
                {getUtilizationIcon(data.utilization)}
                <span className="ml-1">{Math.round(data.utilization * 100)}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Filters and Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-3 sm:space-y-0">
        <div className="flex flex-wrap gap-2">
          <div>
            <label className="sr-only">Filter by type</label>
            <select
              className="form-select"
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
            >
              {resourceTypes.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="sr-only">Sort by</label>
            <select
              className="form-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
            >
              <option value="name">Name</option>
              <option value="capacity">Capacity</option>
              <option value="utilization">Utilization</option>
            </select>
          </div>
        </div>

        <div className="text-sm text-gray-500">
          {filteredAndSortedResources.length} resources found
        </div>
      </div>

      {/* Resources Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredAndSortedResources.map((resource) => (
          <div
            key={resource.id}
            onClick={() => onResourceClick?.(resource)}
            className="card hover:shadow-md transition-shadow cursor-pointer"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className="text-lg font-semibold text-gray-900">{resource.name}</h4>
                <p className="text-sm text-gray-600">
                  {resource.building} • {resource.type.replace('_', ' ').toUpperCase()}
                </p>
              </div>
              <div className={`px-3 py-1 rounded-full text-xs font-medium ${getUtilizationColor(resource.utilization)}`}>
                {Math.round(resource.utilization * 100)}%
              </div>
            </div>

            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Capacity:</span>
                <span className="font-medium">{resource.capacity}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Scheduled:</span>
                <span className="font-medium">{resource.scheduleCount} sessions</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Free Time:</span>
                <span className="font-medium">
                  {Math.round((1 - resource.utilization) * 100)}%
                </span>
              </div>
            </div>

            {/* Features */}
            {resource.features.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-medium text-gray-700 mb-1">Features:</p>
                <div className="flex flex-wrap gap-1">
                  {resource.features.slice(0, 3).map((feature, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700"
                    >
                      {feature}
                    </span>
                  ))}
                  {resource.features.length > 3 && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                      +{resource.features.length - 3} more
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Empty state */}
      {filteredAndSortedResources.length === 0 && (
        <div className="text-center py-12">
          <BuildingOfficeIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No resources found</h3>
          <p className="mt-1 text-sm text-gray-500">
            Try adjusting your filters or add more resources
          </p>
        </div>
      )}
    </div>
  );
}