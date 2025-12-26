import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';

function ConstraintEditor() {
  return (
    <Box>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Constraint Editor
          </Typography>
          <Typography variant="body1">
            This section allows you to define and manage constraints for your scheduling problem.
            You can define hard constraints (requirements that must be met) and soft constraints 
            (preferences that should be optimized).
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}

export default ConstraintEditor;