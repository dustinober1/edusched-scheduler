import React from 'react';
import { Box } from '@mui/material';
import { ResourceList } from '../components/ResourceList';

function ResourceListPage() {
  // Mock data for now
  const resources = [
    { id: 'CS-101', name: 'Computer Science 101', type: 'classroom', capacity: 30 },
    { id: 'MATH-201', name: 'Mathematics 201', type: 'classroom', capacity: 25 },
    { id: 'SCI-LAB', name: 'Science Laboratory', type: 'lab', capacity: 20 }
  ];

  return (
    <Box>
      <ResourceList resources={resources} />
    </Box>
  );
}

export default ResourceListPage;