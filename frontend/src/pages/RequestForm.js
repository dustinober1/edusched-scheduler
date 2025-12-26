import React from 'react';
import { Box } from '@mui/material';
import { RequestForm } from '../components/RequestForm';

function RequestFormPage() {
  // Mock data for now
  const requests = [
    { id: 'CS101', name: 'Intro to Programming', duration: '1.5h', occurrences: 28, capacity: 25 },
    { id: 'MATH201', name: 'Advanced Calculus', duration: '1.5h', occurrences: 26, capacity: 20 }
  ];

  return (
    <Box>
      <RequestForm requests={requests} />
    </Box>
  );
}

export default RequestFormPage;