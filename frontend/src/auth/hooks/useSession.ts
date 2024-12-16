// auth/hooks/useSession.ts
import { useEffect, useCallback, useRef } from 'react';
import { useDispatch } from 'react-redux';
import { storageUtils } from '@/common/utils/storage/storageUtils';
import { authApi } from '../api';
import { setAuth, clearAuth } from '../store/authSlice';
import { useAuthStatus } from './useAuthStatus';
import type { AuthTokens } from '../types';

const AUTH_STORAGE_KEY = 'auth_tokens';
const REFRESH_INTERVAL = 14 * 60 * 1000; // 14 minutes

export function useSession() {
  const dispatch = useDispatch();
  const { isAuthenticated, isInitialized } = useAuthStatus();
  const isRefreshing = useRef(false);

  const validateSession = useCallback(async () => {
    const tokens = storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
    
    if (!tokens?.accessToken) {
      dispatch(clearAuth());
      return false;
    }

    try {
      // Changed from getCurrentUser to getProfile
      const userResponse = await authApi.getProfile();
      if (userResponse.data) {
        dispatch(setAuth({ user: userResponse.data, tokens }));
        return true;
      }
      return false;
    } catch (error) {
      dispatch(clearAuth());
      return false;
    }
  }, [dispatch]);

  const refreshSession = useCallback(async () => {
    if (isRefreshing.current) return false;
    
    isRefreshing.current = true;
    try {
      const tokens = storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
      
      if (!tokens?.refreshToken) {
        dispatch(clearAuth());
        return false;
      }

      const response = await authApi.refreshToken(tokens.refreshToken);
      if (response.data) {
        storageUtils.setItem(AUTH_STORAGE_KEY, response.data);
        await validateSession();
        return true;
      }
      return false;
    } catch {
      dispatch(clearAuth());
      return false;
    } finally {
      isRefreshing.current = false;
    }
  }, [dispatch, validateSession]);

  // Initialize auth state - run only once
  useEffect(() => {
    let mounted = true;

    if (!isInitialized && mounted) {
      validateSession();
    }

    return () => { mounted = false; };
  }, [isInitialized]); // Remove validateSession from dependencies

  // Set up refresh interval with cleanup
  useEffect(() => {
    let mounted = true;
    
    if (!isAuthenticated || !mounted) return;

    const intervalId = setInterval(() => {
      if (mounted) refreshSession();
    }, REFRESH_INTERVAL);

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, [isAuthenticated]); // Remove refreshSession from dependencies

  return {
    validateSession,
    refreshSession
  } as const;
}