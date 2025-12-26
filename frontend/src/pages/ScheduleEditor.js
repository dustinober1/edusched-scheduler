import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Paper, 
  Grid, 
  Card, 
  CardContent, 
  Typography, 
  Button,
  Tabs,
  Tab
} from '@mui/material';
import { ScheduleCalendar } from '../components/ScheduleCalendar';
import { ResourceList } from '../components/ResourceList';
import { RequestForm } from '../components/RequestForm';

function ScheduleEditor() {
  const [activeTab, setActiveTab] = useState(0);
  const [scheduleData, setScheduleData] = useState(null);

  useEffect(() => {
    // Load initial schedule data
    loadScheduleData();
  }, []);

  const loadScheduleData = async () => {
    // In a real implementation, this would call the API
    // For now, we'll use mock data
    const mockData = {
      assignments: [
        {
          id: '1',
          requestId: 'CS101',
          startTime: new Date(2024, 9, 1, 9, 0),
          endTime: new Date(2024, 9, 1, 10, 30),
          resources: ['CS-101']
        },
        {
          id: '2',
          requestId: 'MATH201',
          startTime: new Date(2024, 9, 1, 11, 0),
          endTime: new Date(2024, 9, 1, 12, 30),
          resources: ['MATH-201']
        }
      ],
      resources: [
        { id: 'CS-101', name: 'Computer Science 101', type: 'classroom', capacity: 30 },
        { id: 'MATH-201', name: 'Mathematics 201', type: 'classroom', capacity: 25 }
      ],
      requests: [
        { id: 'CS101', name: 'Intro to Programming', duration: '1.5h', occurrences: 28 },
        { id: 'MATH201', name: 'Advanced Calculus', duration: '1.5h', occurrences: 26 }
      ]
    };
    setScheduleData(mockData);
  };

  const handleSolve = async () => {
    // Call API to solve the schedule
    console.log('Solving schedule...');
  };

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Paper sx={{ p: 2, display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="h6">Schedule Editor</Typography>
          <Button variant="contained" color="primary" onClick={handleSolve}>
            Solve Schedule
          </Button>
        </Paper>
      </Grid>

      <Grid item xs={12}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={handleTabChange}>
            <Tab label="Calendar View" />
            <Tab label="Resources" />
            <Tab label="Requests" />
            <Tab label="Constraints" />
          </Tabs>
        </Box>
      </Grid>

      {activeTab === 0 && (
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            {scheduleData && <ScheduleCalendar assignments={scheduleData.assignments} />}
          </Paper>
        </Grid>
      )}

      {activeTab === 1 && (
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            {scheduleData && <ResourceList resources={scheduleData.resources} />}
          </Paper>
        </Grid>
      )}

      {activeTab === 2 && (
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            {scheduleData && <RequestForm requests={scheduleData.requests} />}
          </Paper>
        </Grid>
      )}

      {activeTab === 3 && (
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6">Constraint Editor</Typography>
            <Typography variant="body1" sx={{ mt: 2 }}>
              Constraint editing functionality coming soon.
            </Typography>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
}

export default ScheduleEditor;