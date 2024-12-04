// src/hooks/useAuth.ts
import { useState, useCallback } from 'react';
import { useDispatch } from 'react-redux';
import { useMutation } from 'react-query';
import { authApi } from '../../services/api/authApi';
import { setAuth, clearAuth } from '../../store/slices/authSlice';

export const useAuth = () => {
  const dispatch = useDispatch();
  const [error, setError] = useState<string | null>(null);

  const loginMutation = useMutation(
    (credentials: { username: string; password: string }) =>
      authApi.login(credentials),
    {
      onSuccess: (response) => {
        const { access_token, refresh_token, user } = response.data;
        dispatch(setAuth({ token: access_token, refreshToken: refresh_token, user }));
        // Store tokens securely
        localStorage.setItem('refreshToken', refresh_token);
      },
      onError: (error: any) => {
        setError(error.message || 'Login failed');
      }
    }
  );

  const logout = useCallback(() => {
    dispatch(clearAuth());
    localStorage.removeItem('refreshToken');
    // Additional cleanup if needed
  }, [dispatch]);

  return {
    login: loginMutation.mutate,
    logout,
    isLoading: loginMutation.isLoading,
    error
  };
};
