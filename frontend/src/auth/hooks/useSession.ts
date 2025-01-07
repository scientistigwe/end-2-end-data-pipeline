// auth/hooks/useSession.ts
import { useEffect, useCallback, useRef } from 'react';
import { useDispatch } from 'react-redux';
import { authApi } from '../api';
import { setAuth, clearAuth } from '../store/authSlice';
import { useAuthStatus } from './useAuthStatus';

const REFRESH_INTERVAL = 14 * 60 * 1000; // 14 minutes

export function useSession() {
  const dispatch = useDispatch();
  const { isAuthenticated, isInitialized } = useAuthStatus();
  const isRefreshing = useRef(false);

  const validateSession = useCallback(async () => {
    try {
      const userResponse = await authApi.getProfile();
      if (userResponse) {
        dispatch(setAuth({ user: userResponse }));
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
      const response = await authApi.refresh();
      if (response) {
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

  useEffect(() => {
    let mounted = true;

    if (!isInitialized && mounted) {
      validateSession();
    }

    return () => { mounted = false; };
  }, [isInitialized]);

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
  }, [isAuthenticated]);

  return {
    validateSession,
    refreshSession
  } as const;
}