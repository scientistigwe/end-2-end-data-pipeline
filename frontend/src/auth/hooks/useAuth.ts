// src/auth/hooks/useAuth.ts
import { useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { useMutation, useQueryClient } from 'react-query';
import { authApi } from '../api/authApi';
import { 
  setAuth, 
  clearAuth, 
  setError, 
  setInitialized,
  startAuthRequest,
  endAuthRequest,
  authSuccess,
  authFailure 
} from '../store/authSlice';
import { 
  selectUser, 
  selectAuthError, 
  selectIsAuthenticated, 
  selectIsInitialized,
  selectIsLoading,
  selectAuthenticationState
} from '../store/selectors';
import type { 
  LoginCredentials, 
  RegisterData,
  ProfileUpdateData,
  ChangePasswordData,
  ResetPasswordData,
  VerifyEmailData,
} from '../types/auth';

export function useAuth() {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  
  const user = useSelector(selectUser);
  const error = useSelector(selectAuthError);
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const isInitialized = useSelector(selectIsInitialized);
  const isLoading = useSelector(selectIsLoading);
  const authState = useSelector(selectAuthenticationState);

  const handleAuthError = useCallback((error: unknown) => {
    const message = error instanceof Error ? error.message : 'An error occurred';
    dispatch(setError(message));
    return message;
  }, [dispatch]);

  // Initialize auth state
  useEffect(() => {
    if (!isInitialized) {
      dispatch(startAuthRequest());
      authApi.getProfile()
        .then((user) => {
          dispatch(authSuccess({ user }));
        })
        .catch(() => {
          dispatch(clearAuth());
        })
        .finally(() => {
          dispatch(setInitialized(true));
          dispatch(endAuthRequest());
        });
    }
  }, [dispatch, isInitialized]);

  // Login mutation
  const { mutateAsync: login, isLoading: isLoggingIn } = useMutation(
    async (credentials: LoginCredentials) => {
      try {
        dispatch(startAuthRequest());
        const response = await authApi.login(credentials);
        dispatch(authSuccess({ user: response.user }));
        navigate('/dashboard');
        return response;
      } catch (error) {
        console.error('Login error:', error);
        const message = handleAuthError(error);
        dispatch(authFailure(message));
        throw error;
      }
    }
  );
  
  // Register mutation
  const { mutateAsync: register, isLoading: isRegistering } = useMutation(
    async (data: RegisterData) => {
      try {
        dispatch(startAuthRequest());
        const response = await authApi.register(data);
        dispatch(authSuccess({ user: response.user }));
        return response;
      } catch (error) {
        console.error('Registration error:', error);
        const message = handleAuthError(error);
        dispatch(authFailure(message));
        throw error;
      }
    }
  );

  // Update profile mutation
  const { mutateAsync: updateProfile, isLoading: isUpdatingProfile } = useMutation(
    async (data: ProfileUpdateData) => {
      try {
        const updatedUser = await authApi.updateProfile(data);
        dispatch(setAuth({ user: updatedUser }));
        return updatedUser;
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  // Logout handler
  const logout = useCallback(async () => {
    try {
      dispatch(startAuthRequest());
      await authApi.logout();
      queryClient.clear();
      dispatch(clearAuth());
      navigate('/login');
    } catch (error) {
      handleAuthError(error);
    } finally {
      dispatch(endAuthRequest());
    }
  }, [dispatch, queryClient, navigate, handleAuthError]);

  // Session refresh handler
  const refreshSession = useCallback(async () => {
    try {
      dispatch(startAuthRequest());
      const response = await authApi.refreshToken();
      if (response?.user) {
        dispatch(authSuccess({ user: response.user }));
        return true;
      }
      return false;
    } catch (error) {
      const message = handleAuthError(error);
      dispatch(authFailure(message));
      return false;
    } finally {
      dispatch(endAuthRequest());
    }
  }, [dispatch, handleAuthError]);

  // Other mutations...
  const { mutateAsync: changePassword, isLoading: isChangingPassword } = useMutation(
    (data: ChangePasswordData) => authApi.changePassword(data)
  );

  const { mutateAsync: resetPassword, isLoading: isResettingPassword } = useMutation(
    (data: ResetPasswordData) => authApi.resetPassword(data)
  );

  const { mutateAsync: verifyEmail, isLoading: isVerifyingEmail } = useMutation(
    (data: VerifyEmailData) => authApi.verifyEmail(data)
  );

  return {
    // State
    user,
    error,
    isAuthenticated,
    isInitialized,
    isLoading,
    authState,

    // Auth operations
    login,
    register,
    logout,
    refreshSession,
    updateProfile,
    changePassword,
    resetPassword,
    verifyEmail,

    // Loading states
    isLoggingIn,
    isRegistering,
    isUpdatingProfile,
    isChangingPassword,
    isResettingPassword,
    isVerifyingEmail,

    // Helpers
    handleAuthError
  } as const;
}

export type AuthHook = ReturnType<typeof useAuth>;