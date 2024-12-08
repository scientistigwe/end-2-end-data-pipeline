// src/auth/hooks/useSession.ts
import { useEffect } from 'react';
import { useAuth } from './useAuth';
import { sessionManager } from '../utils/session';

export function useSession() {
  const { refreshToken } = useAuth();

  useEffect(() => {
    const checkSession = async () => {
      const tokens = sessionManager.getTokens();
      if (tokens?.accessToken && sessionManager.isTokenExpired(tokens.accessToken)) {
        await refreshToken();
      }
    };

    checkSession();

    const refreshInterval = setInterval(checkSession, 14 * 60 * 1000); // 14 minutes

    return () => clearInterval(refreshInterval);
  }, [refreshToken]);

  return {
    isAuthenticated: sessionManager.isAuthenticated(),
    getUser: sessionManager.getUserFromToken.bind(sessionManager),
    clearSession: sessionManager.clearTokens.bind(sessionManager)
  };
}
