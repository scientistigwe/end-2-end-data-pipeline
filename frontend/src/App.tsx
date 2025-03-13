import React, { useEffect } from "react";
import { useDispatch } from "react-redux";
import { BrowserRouter } from "react-router-dom";
import { Provider } from "react-redux";
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
import { setUser, clearAuth } from "./auth/store/authSlice";

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

// Create an AuthEventListener component
const AuthEventListener: React.FC = () => {
  const dispatch = useDispatch();

  useEffect(() => {
    const handleAuthEvent = (event: Event) => {
      const customEvent = event as CustomEvent;

      if (event.type === "auth:login" || event.type === "auth:refresh") {
        if (customEvent.detail?.user) {
          dispatch(setUser(customEvent.detail.user));
        }
      } else if (
        event.type === "auth:logout" ||
        event.type === "auth:token_expired"
      ) {
        dispatch(clearAuth());
      }
    };

    window.addEventListener("auth:login", handleAuthEvent);
    window.addEventListener("auth:logout", handleAuthEvent);
    window.addEventListener("auth:refresh", handleAuthEvent);
    window.addEventListener("auth:token_expired", handleAuthEvent);

    return () => {
      window.removeEventListener("auth:login", handleAuthEvent);
      window.removeEventListener("auth:logout", handleAuthEvent);
      window.removeEventListener("auth:refresh", handleAuthEvent);
      window.removeEventListener("auth:token_expired", handleAuthEvent);
    };
  }, [dispatch]);

  // This component doesn't render anything
  return null;
};

const AppWithProviders: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        {/* Add the event listener component inside the provider tree */}
        <AuthEventListener />
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
