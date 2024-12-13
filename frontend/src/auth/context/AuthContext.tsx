// auth/context/AuthContext.tsx
import { createContext, useContext } from 'react';
import type { User } from '@/common/types/user';
import type { 
  AuthTokens, 
  LoginCredentials, 
  RegisterData 
} from '../types';

export interface AuthContextValue {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  tokens: AuthTokens | null;
  
  // Auth operations
  login: (credentials: LoginCredentials) => Promise<AuthTokens & { user: User }>;
  register: (data: RegisterData) => Promise<{ user: User }>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<boolean>;
  
  // Profile operations
  updateProfile: (data: Partial<User>) => Promise<User>;
  
  // Loading states
  isLoggingIn: boolean;
  isRegistering: boolean;
  isUpdatingProfile: boolean;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within AuthProvider');
  }
  return context;
}

