import React from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow,
  Paper 
} from '@mui/material';

export const ResourceList = ({ resources }) => {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Resources
        </Typography>
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Capacity</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {resources && resources.length > 0 ? (
                resources.map((resource) => (
                  <TableRow key={resource.id}>
                    <TableCell>{resource.id}</TableCell>
                    <TableCell>{resource.name}</TableCell>
                    <TableCell>{resource.type}</TableCell>
                    <TableCell>{resource.capacity}</TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={4} align="center">
                    No resources available
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
};