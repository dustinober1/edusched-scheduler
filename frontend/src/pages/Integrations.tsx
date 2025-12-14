import React, { useState } from 'react';
import {
  CloudArrowUpIcon,
  CloudArrowDownIcon,
  CogIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  LinkIcon,
} from '@heroicons/react/24/outline';

interface Integration {
  id: string;
  name: string;
  type: 'sis' | 'calendar' | 'notification' | 'other';
  description: string;
  status: 'connected' | 'disconnected' | 'error';
  lastSync?: string;
  config?: Record<string, any>;
}

export default function Integrations() {
  const [activeTab, setActiveTab] = useState<'sis' | 'calendar' | 'notifications' | 'other'>('sis');

  const integrations: Integration[] = [
    {
      id: 'canvas',
      name: 'Canvas LMS',
      type: 'sis',
      description: 'Sync course enrollments and student data',
      status: 'connected',
      lastSync: '2024-01-10 14:30',
    },
    {
      id: 'banner',
      name: 'Banner SIS',
      type: 'sis',
      description: 'Student Information System integration',
      status: 'disconnected',
    },
    {
      id: 'google-calendar',
      name: 'Google Calendar',
      type: 'calendar',
      description: 'Export schedules to Google Calendar',
      status: 'connected',
      lastSync: '2024-01-10 09:15',
    },
    {
      id: 'outlook',
      name: 'Outlook Calendar',
      type: 'calendar',
      description: 'Microsoft Outlook calendar sync',
      status: 'error',
    },
    {
      id: 'email',
      name: 'Email Notifications',
      type: 'notification',
      description: 'Send schedule updates via email',
      status: 'connected',
    },
    {
      id: 'sms',
      name: 'SMS Notifications',
      type: 'notification',
      description: 'Text message alerts for urgent changes',
      status: 'disconnected',
    },
  ];

  const tabs = [
    { id: 'sis', name: 'SIS Integrations', count: 2 },
    { id: 'calendar', name: 'Calendar Sync', count: 2 },
    { id: 'notifications', name: 'Notifications', count: 2 },
    { id: 'other', name: 'Other', count: 0 },
  ];

  const filteredIntegrations = integrations.filter(i => i.type === activeTab || (activeTab === 'other' && !['sis', 'calendar', 'notification'].includes(i.type)));

  const getStatusIcon = (status: Integration['status']) => {
    switch (status) {
      case 'connected':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'error':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />;
      default:
        return <div className="h-5 w-5 rounded-full border-2 border-gray-300" />;
    }
  };

  const getStatusBadge = (status: Integration['status']) => {
    const styles = {
      connected: 'bg-green-100 text-green-800',
      error: 'bg-red-100 text-red-800',
      disconnected: 'bg-gray-100 text-gray-800',
    };
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Integrations</h1>
        <p className="mt-2 text-sm text-gray-600">
          Connect external systems and services to streamline your scheduling workflow
        </p>
      </div>

      {/* Integration Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center">
            <LinkIcon className="h-8 w-8 text-green-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Connected</p>
              <p className="text-2xl font-semibold text-gray-900">3</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center">
            <ExclamationTriangleIcon className="h-8 w-8 text-red-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Errors</p>
              <p className="text-2xl font-semibold text-gray-900">1</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center">
            <CloudArrowUpIcon className="h-8 w-8 text-blue-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Last Sync</p>
              <p className="text-2xl font-semibold text-gray-900">5m</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center">
            <CogIcon className="h-8 w-8 text-gray-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Available</p>
              <p className="text-2xl font-semibold text-gray-900">6</p>
            </div>
          </div>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.name}
              {tab.count > 0 && (
                <span className="ml-2 bg-gray-100 text-gray-900 py-0.5 px-2 rounded-full text-xs">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Integration List */}
      <div className="space-y-4">
        {filteredIntegrations.length === 0 ? (
          <div className="card">
            <div className="p-8 text-center text-gray-500">
              <LinkIcon className="mx-auto h-12 w-12 mb-2" />
              <p>No integrations available in this category</p>
            </div>
          </div>
        ) : (
          filteredIntegrations.map((integration) => (
            <div key={integration.id} className="card">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  {getStatusIcon(integration.status)}
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">{integration.name}</h3>
                    <p className="text-sm text-gray-600">{integration.description}</p>
                    {integration.lastSync && (
                      <p className="text-xs text-gray-500 mt-1">Last sync: {integration.lastSync}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  {getStatusBadge(integration.status)}
                  <button className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
                    <CogIcon className="h-4 w-4 mr-1" />
                    Configure
                  </button>
                </div>
              </div>

              {/* Integration Actions */}
              <div className="mt-4 pt-4 border-t border-gray-200 flex justify-between items-center">
                <div className="flex space-x-3">
                  {integration.status === 'connected' ? (
                    <>
                      <button className="text-sm text-primary-600 hover:text-primary-800 font-medium">
                        Sync Now
                      </button>
                      <button className="text-sm text-gray-600 hover:text-gray-800">
                        View Logs
                      </button>
                      <button className="text-sm text-red-600 hover:text-red-800">
                        Disconnect
                      </button>
                    </>
                  ) : (
                    <button className="text-sm text-primary-600 hover:text-primary-800 font-medium">
                      Connect
                    </button>
                  )}
                </div>
                {integration.status === 'error' && (
                  <div className="text-sm text-red-600">
                    Failed to sync - Check configuration
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Add New Integration */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Available Integrations</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { name: 'Blackboard', type: 'LMS', description: 'Learning Management System' },
            { name: 'Moodle', type: 'LMS', description: 'Open-source learning platform' },
            { name: 'Zoom', type: 'Video', description: 'Video conferencing integration' },
            { name: 'Teams', type: 'Video', description: 'Microsoft Teams integration' },
          ].map((service) => (
            <div key={service.name} className="p-4 border border-dashed border-gray-300 rounded-lg hover:border-primary-400 transition-colors">
              <h4 className="font-medium text-gray-900">{service.name}</h4>
              <p className="text-sm text-gray-600 mt-1">{service.type} • {service.description}</p>
              <button className="mt-3 text-sm text-primary-600 hover:text-primary-800 font-medium">
                Learn More →
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}