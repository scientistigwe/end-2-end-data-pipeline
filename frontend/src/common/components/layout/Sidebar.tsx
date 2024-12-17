// src/components/layout/Sidebar.tsx
import { NavLink } from "react-router-dom";
import { useAppSelector } from "@/store/store";
import {
  LayoutDashboard,
  Database,
  GitBranch,
  LineChart,
  Radio,
  FileText,
  Settings,
} from "lucide-react";

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { path: "/sources", label: "Data Sources", icon: Database },
  { path: "/pipelines", label: "Pipelines", icon: GitBranch },
  { path: "/analysis", label: "Analysis", icon: LineChart },
  { path: "/monitoring", label: "Monitoring", icon: Radio },
  { path: "/reports", label: "Reports", icon: FileText },
  { path: "/settings", label: "Settings", icon: Settings },
];

export const Sidebar = () => {
  const isCollapsed = useAppSelector((state) => state.ui.sidebarCollapsed);

  return (
    <aside
      className={`
        bg-card border-r border-border
        transition-all duration-300 ease-in-out
        ${isCollapsed ? "w-16" : "w-64"}
      `}
    >
      <div className="h-full py-4">
        <nav className="space-y-1 px-2">
          {navItems.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) => `
                group flex items-center px-2 py-2 text-sm font-medium rounded-md
                transition-colors duration-200
                ${
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }
              `}
            >
              <Icon
                className={`
                flex-shrink-0 h-5 w-5
                ${isCollapsed ? "mx-auto" : "mr-3"}
              `}
              />
              {!isCollapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>
      </div>
    </aside>
  );
};
