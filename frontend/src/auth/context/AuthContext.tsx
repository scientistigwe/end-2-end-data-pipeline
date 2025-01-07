// auth/context/AuthContext.tsx
import { createContext, useContext } from "react";
import type { AuthContextValue } from "../types/auth";

export type { AuthContextValue };

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined
);

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuthContext must be used within AuthProvider");
  }
  return context;
}
