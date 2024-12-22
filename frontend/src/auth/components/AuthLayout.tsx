// frontend\src\auth\components\AuthLayout.tsx

import React from "react";
import { Link, Outlet } from "react-router-dom";
import PipelineLogo from "@/assets/PipelineLogo";

export const AuthLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <nav className="bg-card border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <Link to="/" className="flex items-center space-x-2">
              <PipelineLogo className="h-8 w-8" />
              <span className="text-xl font-semibold text-foreground">
                Data Pipeline Manager
              </span>
            </Link>
            <div className="space-x-4">
              <Link
                to="/login"
                className="text-muted-foreground hover:text-foreground"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                Register
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="flex min-h-[calc(100vh-4rem)] bg-muted/10">
        <div className="flex-1 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
          <div className="sm:mx-auto sm:w-full sm:max-w-md">
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  );
};
