// auth/providers/AuthProvider.tsx
import React, { useEffect, useMemo } from "react";
import { AuthContext } from "../context";
import { useAuth } from "../hooks/useAuth";
import { useSession } from "../hooks/useSession";
import { storageUtils } from "@/common/utils/storage/storageUtils";
import type { AuthContextValue } from "../context";
import type { AuthTokens } from "../types";

const AUTH_STORAGE_KEY = "auth_tokens";

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const {
    user,
    error,
    isAuthenticated,
    isLoggingIn,
    isRegistering,
    isUpdatingProfile,
    login,
    register,
    logout,
    updateProfile,
  } = useAuth();

  const { validateSession, refreshSession } = useSession();

  const tokens = storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);

  // Initialize auth state
  useEffect(() => {
    validateSession();
  }, []);

  // In AuthProvider.tsx
  const value: AuthContextValue = useMemo(
    () => ({
      // State
      user,
      isAuthenticated,
      error,
      tokens,
      isLoading: isLoggingIn || isRegistering || isUpdatingProfile,

      // Auth operations
      login,
      register,
      logout,
      refreshSession,

      // Profile operations
      updateProfile,

      // Loading states
      isLoggingIn,
      isRegistering,
      isUpdatingProfile,
    }),
    [
      user,
      isAuthenticated,
      error,
      tokens,
      isLoggingIn,
      isRegistering,
      isUpdatingProfile,
      login,
      register,
      logout,
      refreshSession,
      updateProfile,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
