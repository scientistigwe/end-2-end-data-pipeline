import React, { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Outlet, useLocation } from "react-router-dom";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
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

    const getAlertDetails = () => {
      switch (systemHealth.status) {
        case "degraded":
          return {
            icon: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
            bgClass: "bg-yellow-50 border-yellow-200",
            textClass: "text-yellow-800"
          };
        case "critical":
          return {
            icon: <AlertTriangle className="w-5 h-5 text-red-500" />,
            bgClass: "bg-red-50 border-red-200",
            textClass: "text-red-800"
          };
        default:
          return {
            icon: <AlertTriangle className="w-5 h-5 text-gray-500" />,
            bgClass: "bg-gray-50 border-gray-200",
            textClass: "text-gray-800"
          };
      }
    };

    const alertDetails = getAlertDetails();

    return (
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className={`mb-4 p-4 rounded-md border ${alertDetails.bgClass} flex items-center space-x-3`}
      >
        {alertDetails.icon}
        <div>
          <p className={`font-medium ${alertDetails.textClass}`}>
            System Status: {systemHealth.status.toUpperCase()}
          </p>
          {systemHealth.error && (
            <p className="mt-1 text-sm text-muted-foreground">
              {systemHealth.error}
            </p>
          )}
        </div>
      </motion.div>
    );
  }, [systemHealth]);

  // Auth pages render only the Outlet
  if (isAuthPage) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="min-h-screen bg-background"
      >
        <Outlet />
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-background flex flex-col"
    >
      {isAuthenticated && (
        <>
          <Header user={user} />
          <Navbar />
        </>
      )}

      <div className="flex flex-1 overflow-hidden">
        {isAuthenticated && <Sidebar />}

        <main className="flex-1 overflow-y-auto">
          <div className="container mx-auto py-6 px-4 sm:px-6 lg:px-8">
            <AnimatePresence>
              {healthAlert}
            </AnimatePresence>

            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <Outlet />
            </motion.div>
          </div>
        </main>
      </div>
    </motion.div>
  );
};