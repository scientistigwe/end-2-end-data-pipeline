
// frontend\src\main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";

// Import global styles
import "./styles/global/reset.css";
import "./styles/global/base.css";

// Import App and other components
import App from "./App";

// Create MUI theme
const theme = createTheme({
  palette: {
    primary: {
      main: "hsl(var(--primary))",
      contrastText: "hsl(var(--primary-foreground))",
    },
    secondary: {
      main: "hsl(var(--secondary))",
      contrastText: "hsl(var(--secondary-foreground))",
    },
    background: {
      default: "hsl(var(--background))",
      paper: "hsl(var(--card))",
    },
    text: {
      primary: "hsl(var(--foreground))",
      secondary: "hsl(var(--muted-foreground))",
    },
    error: {
      main: "hsl(var(--destructive))",
      contrastText: "hsl(var(--destructive-foreground))",
    },
  },
  typography: {
    fontFamily: "Inter, system-ui, -apple-system, sans-serif",
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          fontFeatureSettings: '"rlig" 1, "calt" 1',
        },
      },
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>
);
