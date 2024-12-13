// auth/hooks/useAuth.ts
import { useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useMutation } from 'react-query';
import { authApi } from '../api';
import { storageUtils } from '@/common/utils/storage/storageUtils';
import { clearAuth, setAuth, setError } from '../store/authSlice';
import { selectUser, selectAuthError, selectIsAuthenticated } from '../store/selectors';
import type { 
  LoginCredentials, 
  RegisterData, 
  AuthTokens
} from '../types/auth';
import type { User } from '@/common/types/user';

const AUTH_STORAGE_KEY = 'auth_tokens';

export function useAuth() {
  const dispatch = useDispatch();
  const user = useSelector(selectUser);
  const error = useSelector(selectAuthError);
  const isAuthenticated = useSelector(selectIsAuthenticated);

  const handleAuthError = useCallback((error: any) => {
    dispatch(setError(error?.message || 'An error occurred'));
  }, [dispatch]);

  // Login mutation
  const { mutateAsync: login, isLoading: isLoggingIn } = useMutation(
    async (credentials: LoginCredentials) => {
      try {
        const response = await authApi.login(credentials);
        if (response.data) {
          const { user, ...tokens } = response.data;
          dispatch(setAuth({ user, tokens }));
        }
        return response.data;
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  // Register mutation
  const { mutateAsync: register, isLoading: isRegistering } = useMutation(
    async (data: RegisterData) => {
      try {
        const response = await authApi.register(data);
        return response.data;
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  // Update profile mutation
  const { mutateAsync: updateProfile, isLoading: isUpdatingProfile } = useMutation(
    async (data: Partial<User>) => {
      try {
        const response = await authApi.updateProfile(data);
        if (response.data) {
          const tokens = storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
          if (tokens) {
            dispatch(setAuth({ user: response.data, tokens }));
          }
        }
        return response.data;
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      storageUtils.removeItem(AUTH_STORAGE_KEY);
      dispatch(clearAuth());
    }
  }, [dispatch]);

  return {
    // State
    user,
    error,
    isAuthenticated,
    
    // Loading states
    isLoggingIn,
    isRegistering,
    isUpdatingProfile,

    // Auth methods
    login,
    register,
    logout,
    updateProfile,
  } as const;
}

export type AuthHook = ReturnType<typeof useAuth>;