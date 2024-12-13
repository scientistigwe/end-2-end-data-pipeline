import React from "react";
import { useLocation } from "react-router-dom";
import { Navbar } from "./Navbar";
import { Sidebar } from "./Sidebar";
import { type RootState } from "../../../store/rootReducer";
import { useAppSelector } from "@/store/store";
import { selectIsAuthenticated } from "../../../auth/store/selectors";

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const location = useLocation();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const systemHealth = useAppSelector(
    (state: RootState) => state.monitoring.systemHealth
  );
  const isAuthPage = ["/login", "/register", "/forgot-password"].includes(
    location.pathname
  );

  if (isAuthPage) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {isAuthenticated && <Navbar />}
      <div className="flex">
        {isAuthenticated && <Sidebar />}
        <main className="flex-1 p-6">
          {systemHealth && systemHealth.status !== "healthy" && (
            <div className="mb-4 p-4 bg-red-100 text-red-700 rounded">
              System Status: {systemHealth.status}
              {systemHealth.error && (
                <p className="mt-1 text-sm">{systemHealth.error}</p>
              )}
            </div>
          )}
          <div className="container mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
};
