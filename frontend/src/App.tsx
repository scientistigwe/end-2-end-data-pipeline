import React, { useEffect } from "react";
import { BrowserRouter } from "react-router-dom";
import { Provider, useDispatch, useSelector } from "react-redux";
import { QueryClient, QueryClientProvider } from "react-query";
import { Toaster } from "react-hot-toast";

// Providers
import { AuthProvider } from "./auth/providers/AuthProvider";
import { AnalysisProvider } from "./analysis/providers/AnalysisProvider";
import { DataSourceProvider } from "./dataSource/providers/DataSourceProvider";
import { DecisionsProvider } from "./decisions/providers/DecisionsProvider";
import { MonitoringProvider } from "./monitoring/providers/MonitoringProvider";
import { PipelineProvider } from "./pipeline/providers/PipelineProvider";
import { RecommendationsProvider } from "./recommendations/providers/RecommendationsProvider";
import { ReportProvider } from "./reports/providers/ReportProvider";

// Routes
import { AppRoutes } from "./routes";
import { store } from "./store/store";

// Auth actions and selectors
import { setInitialized, setLoading } from "./auth/store/authSlice";
import { selectAuthStatus } from "./auth/store/selectors";
import { authApi } from "./auth/api/authApi";

// Styles
import "./styles/global/base.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5000,
    },
  },
});

// Auth initialization component to prevent unnecessary API calls
const AuthInitializer: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const dispatch = useDispatch();
  const authStatus = useSelector(selectAuthStatus);

  useEffect(() => {
    // Check if we need to validate our authentication
    const validateAuth = async () => {
      // Only validate if we think we're authenticated based on persisted state
      if (authStatus === "authenticated") {
        try {
          dispatch(setLoading(true));
          // Silently refresh the token (will update state if successful)
          await authApi.refreshToken();
        } catch (error) {
          console.error("Auth validation failed:", error);
          // The error will be handled by the API call
        } finally {
          dispatch(setLoading(false));
          dispatch(setInitialized(true));
        }
      } else {
        // If we're not authenticated, just mark as initialized
        dispatch(setInitialized(true));
      }
    };

    validateAuth();
  }, [dispatch, authStatus]);

  return <>{children}</>;
};

const AppWithProviders: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AuthInitializer>
          <DataSourceProvider>
            <PipelineProvider>
              <AnalysisProvider>
                <DecisionsProvider>
                  <MonitoringProvider>
                    <RecommendationsProvider>
                      <ReportProvider>
                        <React.Suspense fallback={<div>Loading...</div>}>
                          <AppRoutes />
                        </React.Suspense>
                        <Toaster
                          position="top-right"
                          toastOptions={{
                            duration: 4000,
                            style: {
                              background: "#333",
                              color: "#fff",
                            },
                          }}
                        />
                      </ReportProvider>
                    </RecommendationsProvider>
                  </MonitoringProvider>
                </DecisionsProvider>
              </AnalysisProvider>
            </PipelineProvider>
          </DataSourceProvider>
        </AuthInitializer>
      </AuthProvider>
    </BrowserRouter>
  );
};

const App: React.FC = () => {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <AppWithProviders />
      </QueryClientProvider>
    </Provider>
  );
};

export default App;
