// AuthProvider.tsx
import React, { useEffect, useRef } from "react";
import { useDispatch } from "react-redux";
import { AuthContext } from "../context/AuthContext";
import { useAuth } from "../hooks/useAuth";
import {
  setUser,
  setLoading,
  clearAuth,
  setInitialized,
} from "../store/authSlice";
import { authApi } from "../api/authApi";
import { AuthError } from "../types/errors";
import type { AuthContextValue } from "../types/auth";

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const dispatch = useDispatch();
  const auth = useAuth();
  const isChecking = useRef(false);
  const initialized = useRef(false);

  useEffect(() => {
    const checkAuth = async () => {
      if (isChecking.current || initialized.current) return;

      try {
        isChecking.current = true;
        dispatch(setLoading(true));

        try {
          const userData = await authApi.getProfile();
          if (userData) {
            dispatch(setUser(userData));
          }
        } catch (error) {
          console.error("Authentication check failed:", error);

          // Clear auth state for authentication errors
          if (
            error instanceof AuthError ||
            (error.response &&
              (error.response.status === 401 || error.response.status === 403))
          ) {
            console.log("Auth check failed - clearing auth state");
            dispatch(clearAuth());
          }
        }
      } finally {
        dispatch(setLoading(false));
        dispatch(setInitialized(true));
        isChecking.current = false;
        initialized.current = true;
      }
    };

    checkAuth();

    const handleAuthEvent = () => {
      initialized.current = false;
      checkAuth();
    };

    window.addEventListener("auth:login", handleAuthEvent);
    window.addEventListener("auth:logout", handleAuthEvent);

    return () => {
      window.removeEventListener("auth:login", handleAuthEvent);
      window.removeEventListener("auth:logout", handleAuthEvent);
    };
  }, [dispatch]);

  const value: AuthContextValue = {
    // State
    user: auth.user,
    isAuthenticated: auth.isAuthenticated,
    isLoading: auth.isLoading,
    error: auth.error,
    isInitialized: initialized.current,

    // Auth operations
    login: auth.login,
    register: auth.register,
    logout: auth.logout,
    updateProfile: auth.updateProfile,
    changePassword: auth.changePassword,
    resetPassword: auth.resetPassword,
    verifyEmail: auth.verifyEmail,

    // Loading states
    isLoggingIn: auth.isLoggingIn,
    isRegistering: auth.isRegistering,
    isUpdatingProfile: auth.isUpdatingProfile,
    isChangingPassword: auth.isChangingPassword,
    isResettingPassword: auth.isResettingPassword,
    isVerifyingEmail: auth.isVerifyingEmail,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
