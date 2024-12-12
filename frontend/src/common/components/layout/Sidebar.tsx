// src/components/layout/Sidebar.tsx
import React from "react";
import { NavLink } from "react-router-dom";
import { useAppSelector } from "../../../store/store";

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: "📊" },
  { path: "/sources", label: "Data Sources", icon: "🔌" },
  { path: "/pipelines", label: "Pipelines", icon: "🔄" },
  { path: "/analysis", label: "Analysis", icon: "📈" },
  { path: "/monitoring", label: "Monitoring", icon: "📡" },
  { path: "/reports", label: "Reports", icon: "📑" },
  { path: "/settings", label: "Settings", icon: "⚙️" },
];

export const Sidebar: React.FC = () => {
  const isCollapsed = useAppSelector((state) => state.ui.sidebarCollapsed);

  return (
    <aside className={`bg-white shadow-sm ${isCollapsed ? "w-16" : "w-64"}`}>
      <div className="h-full py-4">
        <nav className="mt-5 flex-1 px-2 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `group flex items-center px-2 py-2 text-sm font-medium rounded-md
                ${
                  isActive
                    ? "bg-blue-50 text-blue-600"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                }`
              }
            >
              <span className="mr-3">{item.icon}</span>
              {!isCollapsed && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>
      </div>
    </aside>
  );
};
