import React, { useState } from 'react';
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
  Paper,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';

export const RequestForm = ({ requests }) => {
  const [open, setOpen] = useState(false);
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    duration: '',
    occurrences: 1,
    capacity: 0
  });

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setFormData({
      id: '',
      name: '',
      duration: '',
      occurrences: 1,
      capacity: 0
    });
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // In a real implementation, this would submit to the API
    console.log('Submitting form:', formData);
    handleClose();
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Session Requests
        </Typography>
        <Button variant="contained" color="primary" onClick={handleClickOpen} sx={{ mb: 2 }}>
          Add Request
        </Button>
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Duration</TableCell>
                <TableCell>Occurrences</TableCell>
                <TableCell>Capacity</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {requests && requests.length > 0 ? (
                requests.map((request) => (
                  <TableRow key={request.id}>
                    <TableCell>{request.id}</TableCell>
                    <TableCell>{request.name}</TableCell>
                    <TableCell>{request.duration}</TableCell>
                    <TableCell>{request.occurrences}</TableCell>
                    <TableCell>{request.capacity || 'N/A'}</TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    No requests available
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <Dialog open={open} onClose={handleClose}>
          <DialogTitle>Add New Request</DialogTitle>
          <form onSubmit={handleSubmit}>
            <DialogContent>
              <TextField
                autoFocus
                margin="dense"
                name="id"
                label="Request ID"
                fullWidth
                variant="outlined"
                value={formData.id}
                onChange={handleChange}
                required
              />
              <TextField
                margin="dense"
                name="name"
                label="Request Name"
                fullWidth
                variant="outlined"
                value={formData.name}
                onChange={handleChange}
                required
              />
              <TextField
                margin="dense"
                name="duration"
                label="Duration (e.g., 1.5h)"
                fullWidth
                variant="outlined"
                value={formData.duration}
                onChange={handleChange}
                required
              />
              <TextField
                margin="dense"
                name="occurrences"
                label="Number of Occurrences"
                type="number"
                fullWidth
                variant="outlined"
                value={formData.occurrences}
                onChange={handleChange}
                required
              />
              <TextField
                margin="dense"
                name="capacity"
                label="Required Capacity"
                type="number"
                fullWidth
                variant="outlined"
                value={formData.capacity}
                onChange={handleChange}
              />
            </DialogContent>
            <DialogActions>
              <Button onClick={handleClose}>Cancel</Button>
              <Button type="submit">Add Request</Button>
            </DialogActions>
          </form>
        </Dialog>
      </CardContent>
    </Card>
  );
};