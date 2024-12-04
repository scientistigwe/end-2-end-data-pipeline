import React from 'react';
import { AppBar, Container, Toolbar, Typography, Paper, Box, ThemeProvider, createTheme } from '@mui/material';
import logo from "./logo.svg";
import "./App.css";
import FileSystemForm from "./components/FileSystemForm";
import PipelineMonitor from "./components/PipelineMonitor";

// Create a theme instance
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

const App = () => {
  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: '#f5f5f5' }}>
        <AppBar position="static">
          <Toolbar>
            <img
              src={logo}
              alt="logo"
              style={{ height: 40, marginRight: 16 }}
            />
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              Pipeline Management System
            </Typography>
          </Toolbar>
        </AppBar>

        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
          <Box sx={{ display: 'grid', gap: 4 }}>
            <Paper elevation={3} sx={{ p: 3 }}>
              <FileSystemForm />
            </Paper>

            <Paper elevation={3} sx={{ p: 3 }}>
              <PipelineMonitor />
            </Paper>
          </Box>
        </Container>
      </Box>
    </ThemeProvider>
  );
};

export default App;