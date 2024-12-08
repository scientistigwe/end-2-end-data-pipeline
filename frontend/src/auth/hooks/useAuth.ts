// src/auth/hooks/useAuth.ts
import { useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useMutation } from 'react-query';
import { authApi } from '../api/authApi';
import { authUtils } from '../utils/authUtils';
import { clearAuth, setAuth } from '../store/authSlice';
import { 
  selectUser, 
  selectAuthError, 
  selectIsAuthenticated 
} from '../store/selectors';
import type { 
  LoginCredentials, 
  RegisterData, 
  ChangePasswordData,
  VerifyEmailData,
  ResetPasswordData,
  User,
  AuthTokens
} from '../types/auth';

export function useAuth() {
  const dispatch = useDispatch();
  const user = useSelector(selectUser);
  const error = useSelector(selectAuthError);
  const isAuthenticated = useSelector(selectIsAuthenticated);

  // Login mutation
  const { mutateAsync: login, isLoading: isLoggingIn } = useMutation(
    async (credentials: LoginCredentials) => {
      const response = await authApi.login(credentials);
      const { user, ...tokens } = response.data;
      authUtils.setTokens(tokens);
      dispatch(setAuth({ user, tokens }));
      return response.data;
    }
  );

  // Register mutation
  const { mutateAsync: register, isLoading: isRegistering } = useMutation(
    async (data: RegisterData) => {
      const response = await authApi.register(data);
      return response.data;
    }
  );

  // Change password mutation
  const { mutateAsync: changePassword, isLoading: isChangingPassword } = useMutation(
    async (data: ChangePasswordData) => {
      const response = await authApi.changePassword(data);
      return response.data;
    }
  );

  // Verify email mutation
  const { mutateAsync: verifyEmail, isLoading: isVerifyingEmail } = useMutation(
    async (data: VerifyEmailData) => {
      const response = await authApi.verifyEmail(data);
      return response.data;
    }
  );

  // Reset password mutation
  const { mutateAsync: resetPassword, isLoading: isResettingPassword } = useMutation(
    async (data: ResetPasswordData) => {
      const response = await authApi.resetPassword(data);
      return response.data;
    }
  );

  // Forgot password mutation
  const { mutateAsync: forgotPassword, isLoading: isForgotPasswordLoading } = useMutation(
    async (email: string) => {
      const response = await authApi.forgotPassword(email);
      return response.data;
    }
  );

  // Update profile mutation
  const { mutateAsync: updateProfile, isLoading: isUpdatingProfile } = useMutation(
    async (data: Partial<User>) => {
      const response = await authApi.updateProfile(data);
      dispatch(setAuth({ user: response.data, tokens: authUtils.getTokens()! }));
      return response.data;
    }
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      authUtils.clearTokens();
      dispatch(clearAuth());
    }
  }, [dispatch]);

  const { mutateAsync: refreshToken, isLoading: isRefreshing } = useMutation<AuthTokens | null>(
    async () => {
      const tokens = authUtils.getTokens();
      if (!tokens?.refreshToken) return null;

      try {
        const response = await authApi.refreshToken(tokens.refreshToken);
        const newTokens = response.data;
        authUtils.setTokens(newTokens);
        return newTokens;
      } catch (error) {
        authUtils.clearTokens();
        dispatch(clearAuth());
        return null;
      }
    }
  );

  return {
    // State
    user,
    error,
    isAuthenticated,
    
    // Loading states
    isLoggingIn,
    isRegistering,
    isChangingPassword,
    isVerifyingEmail,
    isResettingPassword,
    isForgotPasswordLoading,
    isUpdatingProfile,
    isRefreshing,
    
    // Auth methods
    login,
    register,
    logout,
    refreshToken,
    
    // Profile and password methods
    changePassword,
    updateProfile,
    
    // Email verification methods
    verifyEmail,
    forgotPassword,
    resetPassword
  } as const;
}

export type AuthHook = ReturnType<typeof useAuth>;