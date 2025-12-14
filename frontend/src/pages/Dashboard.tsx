import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  CalendarIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  AcademicCapIcon,
  BuildingOfficeIcon,
} from '@heroicons/react/24/outline';
import { analyticsApi, systemApi } from '../api/endpoints';
import { DashboardStats, ActivityLog } from '../types';

export default function Dashboard() {
  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError,
  } = useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: analyticsApi.getDashboardStats,
    refetchInterval: 60000, // Refresh every minute
  });

  const {
    data: activities,
    isLoading: activitiesLoading,
    error: activitiesError,
  } = useQuery({
    queryKey: ['dashboard', 'activities'],
    queryFn: () => systemApi.getInfo().then(res => res.recentActivities || []),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Format time ago helper
  const formatTimeAgo = (date: Date) => {
    const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);

    let interval = seconds / 31536000;
    if (interval > 1) return `${Math.floor(interval)} year${Math.floor(interval) > 1 ? 's' : ''} ago`;

    interval = seconds / 2592000;
    if (interval > 1) return `${Math.floor(interval)} month${Math.floor(interval) > 1 ? 's' : ''} ago`;

    interval = seconds / 86400;
    if (interval > 1) return `${Math.floor(interval)} day${Math.floor(interval) > 1 ? 's' : ''} ago`;

    interval = seconds / 3600;
    if (interval > 1) return `${Math.floor(interval)} hour${Math.floor(interval) > 1 ? 's' : ''} ago`;

    interval = seconds / 60;
    if (interval > 1) return `${Math.floor(interval)} minute${Math.floor(interval) > 1 ? 's' : ''} ago`;

    return 'Just now';
  };

  const quickActions = [
    {
      title: 'Create New Schedule',
      description: 'Start a new scheduling session',
      icon: CalendarIcon,
      href: '/schedule/editor',
      color: 'bg-blue-500',
    },
    {
      title: 'View Current Schedule',
      description: 'Browse the active schedule',
      icon: ClockIcon,
      href: '/schedule/view',
      color: 'bg-green-500',
    },
    {
      title: 'Manage Resources',
      description: 'View and edit rooms and equipment',
      icon: BuildingOfficeIcon,
      href: '/resources',
      color: 'bg-purple-500',
    },
    {
      title: 'Optimization',
      description: 'Run schedule optimization',
      icon: ChartBarIcon,
      href: '/optimization',
      color: 'bg-orange-500',
    },
  ];

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'conflict_resolved':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'conflict_detected':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />;
      case 'assignment_created':
        return <CalendarIcon className="h-5 w-5 text-blue-500" />;
      case 'assignment_cancelled':
        return <ClockIcon className="h-5 w-5 text-gray-500" />;
      case 'optimization_complete':
        return <ChartBarIcon className="h-5 w-5 text-purple-500" />;
      case 'resource_added':
      case 'resource_removed':
        return <BuildingOfficeIcon className="h-5 w-5 text-orange-500" />;
      default:
        return <ClockIcon className="h-5 w-5 text-gray-500" />;
    }
  };

  // Handle loading and error states
  if (statsError || activitiesError) {
    return (
      <div className="space-y-6">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <h3 className="text-sm font-medium text-red-800">Error Loading Dashboard</h3>
          <p className="text-sm text-red-700 mt-1">
            {statsError?.message || activitiesError?.message || 'Failed to load dashboard data'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-sm text-gray-600">
          Overview of your scheduling system status and recent activities
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="card">
          <div className="flex items-center">
            <AcademicCapIcon className="h-8 w-8 text-blue-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Total Courses</p>
              <p className="text-2xl font-semibold text-gray-900">
                {statsLoading ? '-' : stats?.totalCourses || 0}
              </p>
            </div>
          </div>
          <div className="mt-2">
            <Link
              to="/schedule/view"
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              View all →
            </Link>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <CalendarIcon className="h-8 w-8 text-green-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Assignments</p>
              <p className="text-2xl font-semibold text-gray-900">
                {statsLoading ? '-' : stats?.totalAssignments || 0}
              </p>
            </div>
          </div>
          <div className="mt-2">
            <Link
              to="/schedule/editor"
              className="text-sm text-green-600 hover:text-green-800"
            >
              Edit →
            </Link>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <ExclamationTriangleIcon className="h-8 w-8 text-red-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Conflicts</p>
              <p className="text-2xl font-semibold text-gray-900">
                {statsLoading ? '-' : stats?.conflictCount || 0}
              </p>
            </div>
          </div>
          <div className="mt-2">
            <Link
              to="/constraints"
              className="text-sm text-red-600 hover:text-red-800"
            >
              Resolve →
            </Link>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <ChartBarIcon className="h-8 w-8 text-purple-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Utilization</p>
              <p className="text-2xl font-semibold text-gray-900">
                {statsLoading ? '-' : stats?.utilizationRate ? `${stats.utilizationRate.toFixed(1)}%` : '0%'}
              </p>
            </div>
          </div>
          <div className="mt-2">
            <Link
              to="/reports"
              className="text-sm text-purple-600 hover:text-purple-800"
            >
              Reports →
            </Link>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <ClockIcon className="h-8 w-8 text-orange-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Active Optimizations</p>
              <p className="text-2xl font-semibold text-gray-900">
                {statsLoading ? '-' : stats?.activeOptimizations || 0}
              </p>
            </div>
          </div>
          <div className="mt-2">
            <Link
              to="/schedule/editor"
              className="text-sm text-orange-600 hover:text-orange-800"
            >
              Process →
            </Link>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Quick Actions</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((action, index) => (
            <Link
              key={index}
              to={action.href}
              className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-primary-400 hover:bg-primary-50 transition-colors"
            >
              <div className={`p-3 rounded-full ${action.color} mb-3`}>
                <action.icon className="h-6 w-6 text-white" />
              </div>
              <h4 className="text-sm font-medium text-gray-900 text-center">
                {action.title}
              </h4>
              <p className="text-xs text-gray-600 text-center mt-1">
                {action.description}
              </p>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Recent Activity</h3>
        </div>
        <div className="divide-y divide-gray-200">
          {activitiesLoading ? (
            <div className="p-6 text-center text-gray-500">
              <ClockIcon className="mx-auto h-8 w-8 mb-2 animate-spin" />
              Loading activity...
            </div>
          ) : activities && activities.length > 0 ? (
            <ul className="divide-y divide-gray-200">
              {activities.slice(0, 10).map((activity: ActivityLog) => (
                <li key={activity.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      {getActivityIcon(activity.type)}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm text-gray-900">{activity.message}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {formatTimeAgo(new Date(activity.timestamp))}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="p-6 text-center text-gray-500">
              <ClockIcon className="mx-auto h-8 w-8 mb-2" />
              No recent activity
            </div>
          )}
        </div>
        {activities && activities.length > 0 && (
          <div className="px-4 py-3 border-t border-gray-200">
            <Link
              to="/activity"
              className="text-sm text-primary-600 hover:text-primary-800"
            >
              View all activity →
            </Link>
          </div>
        )}
      </div>

      {/* Quick Stats Chart Placeholder */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Weekly Overview</h3>
        </div>
        <div className="p-8 text-center text-gray-500">
          <ChartBarIcon className="mx-auto h-12 w-12 mb-2" />
          <p>Charts and analytics will be displayed here</p>
        </div>
      </div>
    </div>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg
      className={`h-5 w-5 ${className}`}
      fill="none"
      viewBox="0 0 20 20"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="m9 12 2-2 4m-2 4l2-2-2-4m2-4l2-2-2-4"
      />
    </svg>
  );
}