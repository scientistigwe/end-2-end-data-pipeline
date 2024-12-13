// auth/hooks/useSession.ts
import { useEffect, useCallback } from 'react';
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

 const validateSession = useCallback(async () => {
   const tokens = storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
   
   if (!tokens?.accessToken) {
     dispatch(clearAuth());
     return false;
   }

   try {
     // Get current user to validate session
     const userResponse = await authApi.getCurrentUser();
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
   const tokens = storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
   
   if (!tokens?.refreshToken) {
     dispatch(clearAuth());
     return false;
   }

   try {
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
   }
 }, [dispatch, validateSession]);

 // Initialize auth state
 useEffect(() => {
   if (!isInitialized) {
     validateSession();
   }
 }, [isInitialized, validateSession]);

 // Set up refresh interval
 useEffect(() => {
   if (!isAuthenticated) return;

   const intervalId = setInterval(refreshSession, REFRESH_INTERVAL);
   return () => clearInterval(intervalId);
 }, [isAuthenticated, refreshSession]);

 return {
   validateSession,
   refreshSession
 } as const;
}