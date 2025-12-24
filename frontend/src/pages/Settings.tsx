import { useState } from 'react';
import {
  CogIcon,
  BellIcon,
  ShieldCheckIcon,
  CloudArrowUpIcon,
  EyeIcon,
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
} from '@heroicons/react/24/outline';

export default function Settings() {
  const [activeSection, setActiveSection] = useState<'general' | 'notifications' | 'security' | 'data' | 'appearance'>('general');
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('system');

  const sections = [
    { id: 'general', name: 'General', icon: CogIcon },
    { id: 'notifications', name: 'Notifications', icon: BellIcon },
    { id: 'security', name: 'Security', icon: ShieldCheckIcon },
    { id: 'data', name: 'Data & Privacy', icon: CloudArrowUpIcon },
    { id: 'appearance', name: 'Appearance', icon: EyeIcon },
  ];

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-64 bg-white shadow-sm border-r border-gray-200">
        <nav className="p-4 space-y-1">
          {sections.map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id as any)}
              className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeSection === section.id
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <section.icon className="mr-3 h-5 w-5" />
              {section.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6">
        {activeSection === 'general' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-medium text-gray-900">General Settings</h2>
              <p className="mt-1 text-sm text-gray-600">
                Configure basic system settings and preferences
              </p>
            </div>

            <div className="card">
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Institution Name
                  </label>
                  <input
                    type="text"
                    className="form-input"
                    defaultValue="EduSched University"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Time Zone
                  </label>
                  <select className="form-select">
                    <option>America/New_York (UTC-5)</option>
                    <option>America/Chicago (UTC-6)</option>
                    <option>America/Denver (UTC-7)</option>
                    <option>America/Los_Angeles (UTC-8)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Default Semester Duration
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <input
                      type="date"
                      className="form-input"
                      defaultValue="2024-01-15"
                    />
                    <input
                      type="date"
                      className="form-input"
                      defaultValue="2024-05-10"
                    />
                  </div>
                </div>

                <div>
                  <label className="flex items-center">
                    <input type="checkbox" className="form-checkbox" defaultChecked />
                    <span className="ml-2 text-sm text-gray-700">
                      Enable automatic schedule optimization
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeSection === 'notifications' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-medium text-gray-900">Notification Preferences</h2>
              <p className="mt-1 text-sm text-gray-600">
                Choose what notifications you receive and how
              </p>
            </div>

            <div className="card">
              <div className="space-y-6">
                <h3 className="text-md font-medium text-gray-900">Email Notifications</h3>

                <div className="space-y-3">
                  {[
                    'Schedule conflicts detected',
                    'New assignments created',
                    'Schedule optimization completed',
                    'System maintenance alerts',
                    'Weekly summary reports',
                  ].map((notification) => (
                    <label key={notification} className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">{notification}</span>
                      <input type="checkbox" className="form-checkbox" defaultChecked />
                    </label>
                  ))}
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-md font-medium text-gray-900 mb-3">In-App Notifications</h3>
                <div className="space-y-3">
                  {[
                    'Real-time schedule updates',
                    'Constraint violations',
                    'Resource availability changes',
                    'Collaboration requests',
                  ].map((notification) => (
                    <label key={notification} className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">{notification}</span>
                      <input type="checkbox" className="form-checkbox" defaultChecked />
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeSection === 'security' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-medium text-gray-900">Security Settings</h2>
              <p className="mt-1 text-sm text-gray-600">
                Manage your account security and access controls
              </p>
            </div>

            <div className="card">
              <div className="space-y-6">
                <h3 className="text-md font-medium text-gray-900">Authentication</h3>

                <div className="space-y-4">
                  <div>
                    <label className="flex items-center">
                      <input type="checkbox" className="form-checkbox" defaultChecked />
                      <span className="ml-2 text-sm text-gray-700">
                        Require two-factor authentication
                      </span>
                    </label>
                  </div>

                  <div>
                    <label className="flex items-center">
                      <input type="checkbox" className="form-checkbox" />
                      <span className="ml-2 text-sm text-gray-700">
                        Session timeout after 30 minutes of inactivity
                      </span>
                    </label>
                  </div>

                  <div>
                    <label className="flex items-center">
                      <input type="checkbox" className="form-checkbox" defaultChecked />
                      <span className="ml-2 text-sm text-gray-700">
                        Log all access attempts
                      </span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-md font-medium text-gray-900 mb-3">API Access</h3>
                <div className="space-y-3">
                  <button className="text-sm text-primary-600 hover:text-primary-800 font-medium">
                    Generate API Key
                  </button>
                  <div className="text-xs text-gray-500">
                    API keys allow external applications to access EduSched programmatically
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeSection === 'data' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-medium text-gray-900">Data & Privacy</h2>
              <p className="mt-1 text-sm text-gray-600">
                Manage your data and privacy settings
              </p>
            </div>

            <div className="card">
              <div className="space-y-6">
                <h3 className="text-md font-medium text-gray-900">Data Management</h3>

                <div className="space-y-4">
                  <button className="text-sm text-primary-600 hover:text-primary-800 font-medium">
                    Export All Data
                  </button>

                  <button className="text-sm text-primary-600 hover:text-primary-800 font-medium">
                    Schedule Regular Backups
                  </button>

                  <button className="text-sm text-red-600 hover:text-red-800 font-medium">
                    Delete All Data
                  </button>
                </div>

                <div className="text-xs text-gray-500">
                  Data exports include schedules, constraints, resources, and user preferences
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-md font-medium text-gray-900 mb-3">Privacy Settings</h3>
                <div className="space-y-3">
                  <label className="flex items-center">
                    <input type="checkbox" className="form-checkbox" defaultChecked />
                    <span className="ml-2 text-sm text-gray-700">
                      Share anonymized usage data to improve EduSched
                    </span>
                  </label>

                  <label className="flex items-center">
                    <input type="checkbox" className="form-checkbox" />
                    <span className="ml-2 text-sm text-gray-700">
                      Allow analytics tracking
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeSection === 'appearance' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-medium text-gray-900">Appearance</h2>
              <p className="mt-1 text-sm text-gray-600">
                Customize the look and feel of EduSched
              </p>
            </div>

            <div className="card">
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Theme
                  </label>
                  <div className="space-y-3">
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="theme"
                        className="form-radio"
                        checked={theme === 'light'}
                        onChange={() => setTheme('light')}
                      />
                      <SunIcon className="ml-2 h-5 w-5 text-yellow-500" />
                      <span className="ml-2 text-sm text-gray-700">Light</span>
                    </label>

                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="theme"
                        className="form-radio"
                        checked={theme === 'dark'}
                        onChange={() => setTheme('dark')}
                      />
                      <MoonIcon className="ml-2 h-5 w-5 text-gray-500" />
                      <span className="ml-2 text-sm text-gray-700">Dark</span>
                    </label>

                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="theme"
                        className="form-radio"
                        checked={theme === 'system'}
                        onChange={() => setTheme('system')}
                      />
                      <ComputerDesktopIcon className="ml-2 h-5 w-5 text-gray-500" />
                      <span className="ml-2 text-sm text-gray-700">System</span>
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Default Calendar View
                  </label>
                  <select className="form-select">
                    <option>Week View</option>
                    <option>Month View</option>
                    <option>Day View</option>
                    <option>Agenda View</option>
                  </select>
                </div>

                <div>
                  <label className="flex items-center">
                    <input type="checkbox" className="form-checkbox" defaultChecked />
                    <span className="ml-2 text-sm text-gray-700">
                      Show weekends in calendar
                    </span>
                  </label>
                </div>

                <div>
                  <label className="flex items-center">
                    <input type="checkbox" className="form-checkbox" defaultChecked />
                    <span className="ml-2 text-sm text-gray-700">
                      Compact mode for schedule tables
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Save Button */}
        <div className="mt-8 flex justify-end">
          <button className="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}