import React from "react";
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

const App: React.FC = () => {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
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
      </QueryClientProvider>
    </Provider>
  );
};

export default App;
