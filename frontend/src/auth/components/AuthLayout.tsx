// frontend\src\auth\components\AuthLayout.tsx
import React from "react";
import { Link, Outlet } from "react-router-dom";
import { motion } from "framer-motion";
import { ModeToggle } from "@/common/components/modeToggle";
import PipelineLogo from "@/assets/PipelineLogo";

export const AuthLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <motion.nav
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="bg-card border-b border-border shadow-sm"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            {/* Logo and Title */}
            <Link to="/" className="flex items-center space-x-2 group">
              <PipelineLogo className="h-8 w-8 transition-transform group-hover:rotate-6" />
              <span
                className="text-xl font-semibold text-foreground
                transition-colors group-hover:text-primary"
              >
                Analytix Flow
              </span>
            </Link>

            {/* Navigation Actions */}
            <div className="flex items-center space-x-4">
              {/* Dark/Light Mode Toggle */}
              <ModeToggle />

              {/* Authentication Links */}
              <div className="space-x-4">
                <Link
                  to="/login"
                  className="text-muted-foreground hover:text-foreground
                    transition-colors px-2 py-1 rounded-md
                    hover:bg-secondary"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="px-4 py-2 bg-primary text-primary-foreground
                    rounded-md hover:bg-primary/90
                    transition-colors shadow-sm hover:shadow-md"
                >
                  Register
                </Link>
              </div>
            </div>
          </div>
        </div>
      </motion.nav>

      {/* Main Content */}
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="flex-grow flex flex-col justify-center
          py-12 sm:px-6 lg:px-8 bg-muted/5"
      >
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{
              type: "spring",
              stiffness: 300,
              damping: 20,
              delay: 0.3,
            }}
          >
            <Outlet />
          </motion.div>
        </div>
      </motion.div>

      {/* Footer */}
      <motion.footer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        className="bg-card border-t border-border py-6 text-center"
      >
        <div className="container mx-auto px-4">
          <p className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} Data Pipeline Manager. All rights
            reserved.
          </p>
          <div className="mt-2 space-x-4">
            <Link
              to="/privacy"
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Privacy Policy
            </Link>
            <Link
              to="/terms"
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Terms of Service
            </Link>
          </div>
        </div>
      </motion.footer>
    </div>
  );
};
