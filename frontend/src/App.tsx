// src/App.tsx
import React from "react";
import { BrowserRouter as Router } from "react-router-dom";
import { Provider } from "react-redux";
import { QueryClient, QueryClientProvider } from "react-query";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "./context/AuthContext";
import { MainLayout } from "./components/layout/mainLayout";
import { AppRoutes } from "./routes";
import { store } from "./store";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5000,
      cacheTime: 10 * 60 * 1000, // 10 minutes
    },
  },
});

const App: React.FC = () => {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <Router>
          <AuthProvider>
            <MainLayout>
              <AppRoutes />
            </MainLayout>
            <Toaster position="top-right" />
          </AuthProvider>
        </Router>
      </QueryClientProvider>
    </Provider>
  );
};

export default App;
