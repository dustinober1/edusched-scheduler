import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { AppBar, Toolbar, Typography, Container } from '@mui/material';

import ScheduleEditor from './pages/ScheduleEditor';
import ResourceList from './pages/ResourceList';
import RequestForm from './pages/RequestForm';
import ConstraintEditor from './pages/ConstraintEditor';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#e57373',
    },
    background: {
      default: '#f5f5f5',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              EduSched - Educational Scheduling System
            </Typography>
          </Toolbar>
        </AppBar>
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
          <Routes>
            <Route path="/" element={<ScheduleEditor />} />
            <Route path="/schedule" element={<ScheduleEditor />} />
            <Route path="/resources" element={<ResourceList />} />
            <Route path="/requests" element={<RequestForm />} />
            <Route path="/constraints" element={<ConstraintEditor />} />
          </Routes>
        </Container>
      </Router>
    </ThemeProvider>
  );
}

export default App;