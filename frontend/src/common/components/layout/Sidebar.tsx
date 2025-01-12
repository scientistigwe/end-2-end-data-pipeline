import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { NavLink } from "react-router-dom";
import { 
  ChevronsLeft, 
  ChevronsRight 
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/store/store";
import { toggleSidebar } from "@/common/store/ui/uiSlice";
import {
  LayoutDashboard,
  Database,
  GitBranch,
  LineChart,
  Radio,
  FileText,
  Settings,
} from "lucide-react";
import { cn } from "@/common/utils";

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { path: "/data-sources", label: "Data Sources", icon: Database },
  { path: "/pipelines", label: "Pipelines", icon: GitBranch },
  { path: "/analysis", label: "Analysis", icon: LineChart },
  { path: "/monitoring", label: "Monitoring", icon: Radio },
  { path: "/reports", label: "Reports", icon: FileText },
  { path: "/settings", label: "Settings", icon: Settings },
];

export const Sidebar: React.FC = () => {
  const dispatch = useAppDispatch();
  const isCollapsed = useAppSelector((state) => state.ui.sidebarCollapsed);

  const sidebarVariants = {
    collapsed: { 
      width: "4rem", 
      transition: { 
        duration: 0.3,
        ease: "easeInOut"
      }
    },
    expanded: { 
      width: "16rem", 
      transition: { 
        duration: 0.3,
        ease: "easeInOut"
      }
    }
  };

  return (
    <motion.aside
      initial={isCollapsed ? "collapsed" : "expanded"}
      animate={isCollapsed ? "collapsed" : "expanded"}
      variants={sidebarVariants}
      className={cn(
        "bg-card border-r border-border h-full fixed lg:static z-40 overflow-hidden",
        "shadow-sm dark:shadow-md"
      )}
    >
      <div className="h-full py-4 relative flex flex-col">
        {/* Collapse/Expand Button */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => dispatch(toggleSidebar())}
          className="absolute top-2 right-2 z-50 text-muted-foreground hover:text-foreground"
          aria-label={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {isCollapsed ? <ChevronsRight className="h-5 w-5" /> : <ChevronsLeft className="h-5 w-5" />}
        </motion.button>

        {/* Navigation Items */}
        <nav className="space-y-1 px-2 mt-8">
          <AnimatePresence>
            {navItems.map(({ path, label, icon: Icon }) => (
              <NavLink
                key={path}
                to={path}
                className={({ isActive }) => cn(
                  "group flex items-center px-2 py-2 text-sm font-medium rounded-md",
                  "transition-colors duration-200 relative",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                {({ isActive }) => (
                  <>
                    <motion.div
                      layout
                      className="flex items-center w-full"
                    >
                      <Icon
                        className={cn(
                          "flex-shrink-0 h-5 w-5",
                          isCollapsed ? "mx-auto" : "mr-3"
                        )}
                      />
                      <AnimatePresence>
                        {!isCollapsed && (
                          <motion.span
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -10 }}
                            className="flex-1"
                          >
                            {label}
                          </motion.span>
                        )}
                      </AnimatePresence>
                    </motion.div>
                    
                    {isActive && !isCollapsed && (
                      <motion.div
                        layoutId="active-indicator"
                        className="absolute right-2 h-1.5 w-1.5 bg-primary rounded-full"
                      />
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </AnimatePresence>
        </nav>
      </div>
    </motion.aside>
  );
};