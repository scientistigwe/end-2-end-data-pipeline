import React from "react";
import { useNavigate } from "react-router-dom";
import { useAppSelector } from "@/store/store";
import { useAuth } from "@/auth/hooks/useAuth";
import { UserMenu } from "./UserMenu";

export const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const user = useAppSelector((state) => state.auth.user);

  const navItems = [
    { label: "Overview", href: "/dashboard" },
    { label: "Pipelines", href: "/pipelines" },
    { label: "Analysis", href: "/analysis" },
    { label: "Reports", href: "/reports" },
  ];

  return (
    <nav className="bg-card border-b border-border h-16">
      <div className="h-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-full">
          <div className="flex items-center space-x-4">
            {navItems.map((item) => (
              <button
                key={item.href}
                onClick={() => navigate(item.href)}
                className="px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent rounded-md"
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="flex items-center space-x-4">
            <div className="text-sm text-muted-foreground">{user?.email}</div>
            <UserMenu user={user} onLogout={logout} />
          </div>
        </div>
      </div>
    </nav>
  );
};
