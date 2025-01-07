// auth/hooks/useAuth.ts
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { useMutation } from 'react-query';
import { authApi } from '../api/authApi';
import {
  setUser,
  setError,
  setLoading,
  clearAuth,
} from '../store/authSlice';
import {
  selectUser,
  selectAuthError,
  selectIsAuthenticated,
  selectIsLoading,
} from '../store/selectors';
import type { 
  LoginCredentials, 
  RegisterData, 
  ProfileUpdateData,
  ChangePasswordData,
  ResetPasswordData,
  VerifyEmailData
} from '../types/auth';
import type { User } from '@/common/types/user';

export function useAuth() {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  // State selectors
  const user = useSelector(selectUser);
  const error = useSelector(selectAuthError);
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const isLoading = useSelector(selectIsLoading);

  // Handle errors
  const handleAuthError = useCallback(
    (error: unknown) => {
      const message = error instanceof Error ? error.message : 'An error occurred';
      dispatch(setError(message));
      return message;
    },
    [dispatch]
  );

  // Login mutation
  const { mutateAsync: loginMutation, isLoading: isLoggingIn } = useMutation(
    async (credentials: LoginCredentials) => {
      try {
        dispatch(setLoading(true));
        const response = await authApi.login(credentials);
        
        // Get user profile after successful login
        const userProfile = await authApi.getProfile();
        dispatch(setUser(userProfile));
        
        navigate('/dashboard');
        return true;
      } catch (error) {
        handleAuthError(error);
        return false;
      } finally {
        dispatch(setLoading(false));
      }
    }
  );

  // Register mutation
  const { mutateAsync: registerMutation, isLoading: isRegistering } = useMutation(
    async (data: RegisterData) => {
      try {
        dispatch(setLoading(true));
        const response = await authApi.register(data);
        
        // Get user profile after successful registration
        const userProfile = await authApi.getProfile();
        dispatch(setUser(userProfile));
        
        navigate('/dashboard');
        return true;
      } catch (error) {
        handleAuthError(error);
        return false;
      } finally {
        dispatch(setLoading(false));
      }
    }
  );

  // Update profile mutation
  const { mutateAsync: updateProfileMutation, isLoading: isUpdatingProfile } = useMutation(
    async (data: ProfileUpdateData) => {
      try {
        const updatedUser = await authApi.updateProfile(data);
        dispatch(setUser(updatedUser));
        return updatedUser;
      } catch (error) {
        handleAuthError(error);
        throw error;
      }
    }
  );

  // Change password mutation
  const { mutateAsync: changePasswordMutation, isLoading: isChangingPassword } = useMutation(
    async (data: ChangePasswordData) => {
      try {
        await authApi.changePassword(data);
        return true;
      } catch (error) {
        handleAuthError(error);
        return false;
      }
    }
  );

  // Reset password mutation
  const { mutateAsync: resetPasswordMutation, isLoading: isResettingPassword } = useMutation(
    async (data: ResetPasswordData) => {
      try {
        await authApi.resetPassword(data);
        return true;
      } catch (error) {
        handleAuthError(error);
        return false;
      }
    }
  );

  // Verify email mutation
  const { mutateAsync: verifyEmailMutation, isLoading: isVerifyingEmail } = useMutation(
    async (data: VerifyEmailData) => {
      try {
        await authApi.verifyEmail(data);
        return true;
      } catch (error) {
        handleAuthError(error);
        return false;
      }
    }
  );

  // Logout handler
  const logout = useCallback(async () => {
    try {
      dispatch(setLoading(true));
      await authApi.logout();
      dispatch(clearAuth());
      navigate('/login');
    } catch (error) {
      handleAuthError(error);
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch, navigate, handleAuthError]);

  return {
    // State
    user,
    error,
    isAuthenticated,
    isLoading,

    // Auth operations
    login: loginMutation,
    register: registerMutation,
    logout,
    updateProfile: updateProfileMutation,
    changePassword: changePasswordMutation,
    resetPassword: resetPasswordMutation,
    verifyEmail: verifyEmailMutation,

    // Loading states
    isLoggingIn,
    isRegistering,
    isUpdatingProfile,
    isChangingPassword,
    isResettingPassword,
    isVerifyingEmail,
  };
}

export type AuthHook = ReturnType<typeof useAuth>;