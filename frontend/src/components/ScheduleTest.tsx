import React, { useState, useEffect } from 'react';
import { Schedule, Assignment } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface TestResult {
  test: string;
  passed: boolean;
  details: string;
  timestamp: string;
}

export const ScheduleTest: React.FC = () => {
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [currentSchedule, setCurrentSchedule] = useState<Schedule | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);

  const logResult = (testName: string, passed: boolean, details: string) => {
    const result: TestResult = {
      test: testName,
      passed,
      details,
      timestamp: new Date().toLocaleTimeString()
    };
    setTestResults(prev => [...prev, result]);
  };

  // Test API connectivity
  const testApiHealth = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      const data = await response.json();
      if (response.ok) {
        logResult('API Health Check', true, `Status: ${data.status}`);
      } else {
        logResult('API Health Check', false, 'API not responding');
      }
    } catch (error) {
      logResult('API Health Check', false, `Error: ${error}`);
    }
  };

  // Test creating a schedule
  const testCreateSchedule = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/schedules/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          solver: 'heuristic',
          seed: 42,
          optimize: true
        })
      });

      const data = await response.json();
      if (response.ok) {
        setCurrentSchedule(data);
        logResult('Create Schedule', true, `Created schedule with ${data.total_assignments} assignments`);
      } else {
        logResult('Create Schedule', false, `Error: ${data.detail}`);
      }
    } catch (error) {
      logResult('Create Schedule', false, `Error: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Test fetching schedules
  const testFetchSchedules = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/schedules/`);
      const data = await response.json();
      if (response.ok) {
        logResult('Fetch Schedules', true, `Found ${data.total} schedules`);
      } else {
        logResult('Fetch Schedules', false, 'Failed to fetch schedules');
      }
    } catch (error) {
      logResult('Fetch Schedules', false, `Error: ${error}`);
    }
  };

  // Test WebSocket connection
  const testWebSocket = () => {
    const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'}?user_id=test-user-${Date.now()}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      logResult('WebSocket Connection', true, 'Connected successfully');
      setWsConnection(ws);

      // Send a test message
      ws.send(JSON.stringify({
        type: 'ping',
        timestamp: new Date().toISOString()
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      logResult('WebSocket Message', true, `Received: ${data.type || 'unknown'}`);
    };

    ws.onerror = (error) => {
      logResult('WebSocket Connection', false, 'Connection error');
    };

    ws.onclose = () => {
      logResult('WebSocket Connection', false, 'Connection closed');
      setWsConnection(null);
    };
  };

  // Run all tests
  const runAllTests = async () => {
    setTestResults([]);
    await testApiHealth();
    await testCreateSchedule();
    if (currentSchedule) {
      await testFetchSchedules();
    }
    testWebSocket();
  };

  // Clear results
  const clearResults = () => {
    setTestResults([]);
    setCurrentSchedule(null);
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-3xl font-bold mb-6">EduSched Frontend Test Suite</h1>

        <div className="flex gap-4 mb-6">
          <button
            onClick={runAllTests}
            disabled={isLoading}
            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {isLoading ? 'Running Tests...' : 'Run All Tests'}
          </button>
          <button
            onClick={clearResults}
            className="px-6 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Clear Results
          </button>
        </div>

        {/* Test Results */}
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">Test Results</h2>
          <div className="space-y-2">
            {testResults.map((result, index) => (
              <div
                key={index}
                className={`p-3 rounded ${result.passed ? 'bg-green-100 border-green-300' : 'bg-red-100 border-red-300'} border`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">
                    {result.passed ? '✅' : '❌'} {result.test}
                  </span>
                  <span className="text-sm text-gray-600">{result.timestamp}</span>
                </div>
                <div className="text-sm text-gray-700 mt-1">{result.details}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Current Schedule Display */}
        {currentSchedule && (
          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-4">Current Schedule</h2>
            <div className="bg-gray-50 p-4 rounded">
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <span className="font-medium">ID:</span> {currentSchedule.id}
                </div>
                <div>
                  <span className="font-medium">Status:</span> {currentSchedule.status}
                </div>
                <div>
                  <span className="font-medium">Total Assignments:</span> {currentSchedule.total_assignments}
                </div>
                <div>
                  <span className="font-medium">Solver Time:</span> {currentSchedule.solver_time_ms}ms
                </div>
              </div>

              {/* Assignment Table */}
              <div>
                <h3 className="font-medium mb-2">Assignments:</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Course</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Teacher</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Room</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Start Time</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">End Time</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {currentSchedule.assignments.slice(0, 10).map((assignment, index) => (
                        <tr key={index}>
                          <td className="px-4 py-2 whitespace-nowrap text-sm">
                            {assignment.course_code || 'N/A'}
                          </td>
                          <td className="px-4 py-2 whitespace-nowrap text-sm">
                            {assignment.teacher_name || 'N/A'}
                          </td>
                          <td className="px-4 py-2 whitespace-nowrap text-sm">
                            {assignment.room_name || 'N/A'}
                          </td>
                          <td className="px-4 py-2 whitespace-nowrap text-sm">
                            {new Date(assignment.start_time).toLocaleString()}
                          </td>
                          <td className="px-4 py-2 whitespace-nowrap text-sm">
                            {new Date(assignment.end_time).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {currentSchedule.assignments.length > 10 && (
                    <div className="text-sm text-gray-500 mt-2">
                      Showing 10 of {currentSchedule.assignments.length} assignments
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* WebSocket Status */}
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">WebSocket Status</h2>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${wsConnection ? 'bg-green-500' : 'bg-gray-300'}`}></div>
            <span>{wsConnection ? 'Connected' : 'Disconnected'}</span>
            {wsConnection && (
              <button
                onClick={() => {
                  wsConnection.close();
                  setWsConnection(null);
                }}
                className="ml-4 px-4 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
              >
                Disconnect
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};