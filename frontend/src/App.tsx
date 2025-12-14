import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';

// Pages
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ScheduleEditor from './pages/ScheduleEditor';
import ScheduleViewer from './pages/ScheduleViewer';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import Resources from './pages/Resources';
import Constraints from './pages/Constraints';
import Optimization from './pages/Optimization';
import Integrations from './pages/Integrations';

// Components
import LoadingSpinner from './components/ui/LoadingSpinner';
import ErrorBoundary from './components/ErrorBoundary';
import { ScheduleTest } from './components/ScheduleTest';

// Real-time
import { RealtimeProvider } from './contexts/RealtimeContext';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
    mutations: {
      retry: 1,
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <RealtimeProvider>
          <Router>
          <div className="min-h-screen bg-gray-50">
            <Routes>
              <Route path="/" element={<Layout />}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard" element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <Dashboard />
                  </Suspense>
                } />
                <Route path="schedule">
                  <Route path="editor" element={
                    <Suspense fallback={<LoadingSpinner />}>
                      <ScheduleEditor />
                    </Suspense>
                  } />
                  <Route path="view" element={
                    <Suspense fallback={<LoadingSpinner />}>
                      <ScheduleViewer />
                    </Suspense>
                  } />
                </Route>
                <Route path="resources" element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <Resources />
                  </Suspense>
                } />
                <Route path="constraints" element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <Constraints />
                  </Suspense>
                } />
                <Route path="optimization" element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <Optimization />
                  </Suspense>
                } />
                <Route path="reports" element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <Reports />
                  </Suspense>
                } />
                <Route path="integrations" element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <Integrations />
                  </Suspense>
                } />
                <Route path="settings" element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <Settings />
                  </Suspense>
                } />
              </Route>
              {/* Test route for development */}
              <Route path="/test" element={<ScheduleTest />} />
            </Routes>
          </div>
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                duration: 3000,
                iconTheme: {
                  primary: '#22c55e',
                  secondary: '#fff',
                },
              },
              error: {
                duration: 5000,
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#fff',
                },
              },
            }}
          />
          </Router>
        </RealtimeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;