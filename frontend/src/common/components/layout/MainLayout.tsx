import React, { useMemo } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Header } from "./Header";
import { Navbar } from "./Navbar";
import { Sidebar } from "./Sidebar";
import { useAppSelector } from "@/store/store";
import { selectIsAuthenticated } from "@/auth/store/selectors";

export const MainLayout: React.FC = () => {
  const location = useLocation();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const systemHealth = useAppSelector((state) => state.monitoring.systemHealth);
  const user = useAppSelector((state) => state.auth.user);

  const authPages = useMemo(
    () => ["/login", "/register", "/forgot-password"],
    []
  );

  const isAuthPage = useMemo(
    () => authPages.includes(location.pathname),
    [location.pathname, authPages]
  );

  const healthAlert = useMemo(() => {
    if (!systemHealth || systemHealth.status === "healthy") return null;
    return (
      <div className="mb-4 p-4 bg-destructive/10 text-destructive rounded-md">
        <p className="font-medium">System Status: {systemHealth.status}</p>
        {systemHealth.error && (
          <p className="mt-1 text-sm">{systemHealth.error}</p>
        )}
      </div>
    );
  }, [systemHealth]);

  if (isAuthPage) {
    return <Outlet />;
  }

  return (
    <div className="min-h-screen bg-background">
      {isAuthenticated && (
        <>
          <Header user={user} />
          <Navbar />
        </>
      )}
      <div className="flex h-[calc(100vh-8rem)]">
        {" "}
        {/* Adjusted for Header + Navbar height */}
        {isAuthenticated && <Sidebar />}
        <main className="flex-1 overflow-y-auto">
          <div className="container mx-auto py-6 px-4 sm:px-6 lg:px-8">
            {healthAlert}
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
