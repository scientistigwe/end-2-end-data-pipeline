// auth/hooks/useAuth.ts
import { useCallback, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useMutation, useQueryClient } from 'react-query';
import { authApi } from '../api/authApi';
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
  ProfileUpdateData,
  ChangePasswordData,
  ResetPasswordData,
  VerifyEmailData,
} from '../types/auth';

const AUTH_STORAGE_KEY = 'auth_tokens';

export function useAuth() {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();
  
  const user = useSelector(selectUser);
  const error = useSelector(selectAuthError);
  const tokens = useSelector(selectAuthTokens);
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const isInitialized = useSelector(selectIsInitialized);

  const handleAuthError = useCallback((error: unknown) => {
    const message = error instanceof Error ? error.message : 'An error occurred';
    dispatch(setError(message));
    return message;
  }, [dispatch]);

  // Initialize auth state from storage
  useEffect(() => {
    if (!isInitialized) {
      const storedTokens = storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
      if (storedTokens?.access_token) {
        authApi.getProfile()
          .then((user) => {
            dispatch(setAuth({ user, tokens: storedTokens }));
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

  // Login mutation
const { mutateAsync: login, isLoading: isLoggingIn } = useMutation(
  async (credentials: LoginCredentials) => {
    try {
      const response = await authApi.login(credentials);
      
      // Check for required properties
      if (!response.tokens || !response.user) {
        throw new Error('Invalid login response format');
      }

      // Update auth state
      dispatch(setAuth({ 
        user: response.user, 
        tokens: response.tokens 
      }));

      return response;
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
        const { data: responseData } = response;
        dispatch(setAuth({ user: responseData.user, tokens: responseData.tokens }));
        return response;
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  // Update profile mutation
  const { mutateAsync: updateProfile, isLoading: isUpdatingProfile } = useMutation(
    async (data: ProfileUpdateData) => {
      try {
        const updatedUser = await authApi.updateProfile(data);
        if (tokens) {
          dispatch(setAuth({ user: updatedUser, tokens }));
        }
        return updatedUser;
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  // Change password mutation
  const { mutateAsync: changePassword, isLoading: isChangingPassword } = useMutation(
    async (data: ChangePasswordData) => {
      try {
        await authApi.changePassword(data);
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  // Reset password mutation
  const { mutateAsync: resetPassword, isLoading: isResettingPassword } = useMutation(
    async (data: ResetPasswordData) => {
      try {
        await authApi.resetPassword(data);
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  // Verify email mutation
  const { mutateAsync: verifyEmail, isLoading: isVerifyingEmail } = useMutation(
    async (data: VerifyEmailData) => {
      try {
        await authApi.verifyEmail(data);
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  // Logout handler
  const logout = useCallback(async () => {
    try {
      if (isAuthenticated) {
        await authApi.logout();
      }
    } catch (error) {
      handleAuthError(error);
    } finally {
      storageUtils.removeItem(AUTH_STORAGE_KEY);
      queryClient.clear();
      dispatch(clearAuth());
    }
  }, [dispatch, queryClient, isAuthenticated, handleAuthError]);

  // Token refresh handler
  const refreshToken = useCallback(async () => {
    try {
      const currentTokens = storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
      if (!currentTokens?.refresh_token) {
        throw new Error('No refresh token available');
      }

      const newTokens = await authApi.refreshToken(currentTokens.refresh_token);
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
    user,
    error,
    isAuthenticated,
    isInitialized,
    isLoggingIn,
    isRegistering,
    isUpdatingProfile,
    isChangingPassword,
    isResettingPassword,
    isVerifyingEmail,
    login,
    register,
    logout,
    updateProfile,
    changePassword,
    resetPassword,
    verifyEmail,
    refreshToken,
    handleAuthError
  } as const;
}

export type AuthHook = ReturnType<typeof useAuth>;