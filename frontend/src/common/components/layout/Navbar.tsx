// src/components/layout/Navbar.tsx
import React from "react";
import { useNavigate } from "react-router-dom";
import { useAppSelector } from "../../../store/store";
import { useAuth } from "../../../auth/hooks/useAuth";

export const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const user = useAppSelector((state) => state.auth.user);

  return (
    <nav className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              {/* Add your logo here */}
              <span className="text-xl font-bold">Data Pipeline</span>
            </div>
          </div>

          <div className="flex items-center">
            <div className="ml-3 relative">
              <button
                className="max-w-xs flex items-center text-sm rounded-full focus:outline-none"
                onClick={() => navigate("/settings/profile")}
              >
                <span className="mr-2">{user?.email}</span>
                {/* Add user avatar or icon here */}
              </button>
            </div>
            <button
              onClick={logout}
              className="ml-4 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};
