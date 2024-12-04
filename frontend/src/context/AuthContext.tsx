// contexts/AuthContext.tsx
import React, { createContext, useContext, useEffect } from "react";
import { useDispatch } from "react-redux";
import { useAppSelector } from "../store";
import {
  selectIsAuthenticated,
  setAuth,
  clearAuth,
} from "../store/slices/authSlice";
import { authApi } from "../services/api/authApi";

interface AuthContextType {
  isAuthenticated: boolean;
  refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const dispatch = useDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);

  const refreshAuth = async () => {
    const storedToken = localStorage.getItem("refreshToken");
    if (!storedToken) return;

    try {
      const { data } = await authApi.refreshToken(storedToken);
      dispatch(
        setAuth({
          token: data.access_token,
          refreshToken: data.refresh_token,
          user: data.user,
        })
      );

      // Update stored refresh token
      localStorage.setItem("refreshToken", data.refresh_token);
    } catch (error) {
      dispatch(clearAuth());
      localStorage.removeItem("refreshToken");
    }
  };

  useEffect(() => {
    refreshAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, refreshAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuthContext = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuthContext must be used within an AuthProvider");
  }
  return context;
};
