import React from "react";
import { motion } from "framer-motion";
import { useLocation, useNavigate } from "react-router-dom";
import {
  LayoutGrid,
  Share2,
  BarChart3,
  FileText,
  Activity
} from "lucide-react";
import { useAppSelector } from "@/store/store";
import { useAuth } from "@/auth/hooks/useAuth";
import { UserMenu } from "./UserMenu";
import { cn } from "@/common/utils";

export const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();
  const user = useAppSelector((state) => state.auth.user);

  const navItems = [
    {
      label: "Overview",
      href: "/dashboard",
      icon: LayoutGrid
    },
    {
      label: "Pipelines",
      href: "/pipelines",
      icon: Share2
    },
    {
      label: "Analysis",
      href: "/analysis",
      icon: BarChart3
    },
    {
      label: "Reports",
      href: "/reports",
      icon: FileText
    },
    {
      label: "Activity",
      href: "/activity",
      icon: Activity
    }
  ];

  return (
    <motion.nav
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="sticky top-16 z-40 bg-card border-b border-border h-16"
    >
      <div className="h-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-full items-center">
          {/* Navigation Items */}
          <div className="flex items-center space-x-1">
            {navItems.map((item) => {
              const isActive = location.pathname.startsWith(item.href);
              const Icon = item.icon;

              return (
                <motion.button
                  key={item.href}
                  onClick={() => navigate(item.href)}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className={cn(
                    "flex items-center space-x-2 px-3 py-2 text-sm rounded-md transition-all duration-300",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </motion.button>
              );
            })}
          </div>

          {/* User Section */}
          <div className="flex items-center space-x-4">
            {/* User Email */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-sm text-muted-foreground max-w-[200px] truncate"
              title={user?.email}
            >
              {user?.email}
            </motion.div>

            {/* User Menu */}
            <UserMenu user={user} onLogout={logout} />
          </div>
        </div>
      </div>
    </motion.nav>
  );
};