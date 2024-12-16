// src/auth/hooks/useAuth.ts
import { useCallback, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useMutation, useQueryClient } from 'react-query';
import { authApi } from '../api';
import { storageUtils } from '@/common/utils/storage/storageUtils';
import { 
  clearAuth, 
  setAuth, 
  setError, 
  setInitialized 
} from '../store/authSlice';
import { 
  selectUser, 
  selectAuthError, 
  selectIsAuthenticated, 
  selectIsInitialized,
  selectAuthTokens 
} from '../store/selectors';
import type { 
  LoginCredentials, 
  RegisterData, 
  AuthTokens, 
  ForgotPasswordData,
  ResetPasswordData
} from '../types/auth';
import type { User } from '@/common/types/user';
import type { ApiResponse } from '@/common/types/api';

const AUTH_STORAGE_KEY = 'auth_tokens';

export function useAuth() {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();
  
  // Selectors
  const user = useSelector(selectUser);
  const error = useSelector(selectAuthError);
  const tokens = useSelector(selectAuthTokens);
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const isInitialized = useSelector(selectIsInitialized);

  // Error Handler
  const handleAuthError = useCallback((error: unknown) => {
    const message = error instanceof Error ? error.message : 'An error occurred';
    dispatch(setError(message));
    return message;
  }, [dispatch]);

  // Initialize auth state from storage
  useEffect(() => {
    if (!isInitialized) {
      const storedTokens = storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
      if (storedTokens?.accessToken) {
        authApi.getProfile()
          .then((response) => {
            dispatch(setAuth({ user: response.data, tokens: storedTokens }));
          })
          .catch(() => {
            storageUtils.removeItem(AUTH_STORAGE_KEY);
            dispatch(clearAuth());
          })
          .finally(() => {
            dispatch(setInitialized(true));
          });
      } else {
        dispatch(setInitialized(true));
      }
    }
  }, [dispatch, isInitialized]);

  // Auth Mutations
  const { mutateAsync: login, isLoading: isLoggingIn } = useMutation(
    async (credentials: LoginCredentials): Promise<ApiResponse<{ user: User; tokens: AuthTokens }>> => {
      try {
        const response = await authApi.login(credentials);
        const { user, ...tokens } = response.data;
        storageUtils.setItem(AUTH_STORAGE_KEY, tokens);
        dispatch(setAuth({ user, tokens }));
        return response;
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  const { mutateAsync: register, isLoading: isRegistering } = useMutation(
    async (data: RegisterData): Promise<ApiResponse<{ user: User; tokens: AuthTokens }>> => {
      try {
        const response = await authApi.register(data);
        const { user, ...tokens } = response.data;
        storageUtils.setItem(AUTH_STORAGE_KEY, tokens);
        dispatch(setAuth({ user, tokens }));
        return response;
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  const { mutateAsync: updateProfile, isLoading: isUpdatingProfile } = useMutation(
    async (data: Partial<User>): Promise<ApiResponse<User>> => {
      try {
        const response = await authApi.updateProfile(data);
        if (response.data && tokens) {
          dispatch(setAuth({ user: response.data, tokens }));
        }
        return response;
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  const { mutateAsync: forgotPassword, isLoading: isRequestingReset } = useMutation(
    async (data: ForgotPasswordData): Promise<ApiResponse<void>> => {
      try {
        return await authApi.forgotPassword(data);
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  const { mutateAsync: resetPassword, isLoading: isResettingPassword } = useMutation(
    async (data: ResetPasswordData): Promise<ApiResponse<void>> => {
      try {
        return await authApi.resetPassword(data);
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  const logout = useCallback(async () => {
    try {
      if (isAuthenticated) {
        await authApi.logout();
      }
    } catch (error) {
      handleAuthError(error);
    } finally {
      storageUtils.removeItem(AUTH_STORAGE_KEY);
      queryClient.clear(); // Clear all React Query cache
      dispatch(clearAuth());
    }
  }, [dispatch, queryClient, isAuthenticated, handleAuthError]);

  const refreshToken = useCallback(async () => {
    try {
      const currentTokens = storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
      if (!currentTokens?.refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await authApi.refreshToken(currentTokens.refreshToken);
      const newTokens = response.data;
      storageUtils.setItem(AUTH_STORAGE_KEY, newTokens);
      
      if (user) {
        dispatch(setAuth({ user, tokens: newTokens }));
      }
      
      return newTokens;
    } catch (error) {
      handleAuthError(error);
      await logout();
      throw error;
    }
  }, [dispatch, user, logout, handleAuthError]);

  return {
    // State
    user,
    error,
    isAuthenticated,
    isInitialized,
    
    // Loading states
    isLoggingIn,
    isRegistering,
    isUpdatingProfile,
    isRequestingReset,
    isResettingPassword,

    // Auth methods
    login,
    register,
    logout,
    updateProfile,
    forgotPassword,
    resetPassword,
    refreshToken,
    
    // Utils
    handleAuthError
  } as const;
}

export type AuthHook = ReturnType<typeof useAuth>;