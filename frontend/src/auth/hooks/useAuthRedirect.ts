// auth/hooks/useAuthRedirect.ts
import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStatus } from './useAuthStatus';
import { AUTH_API_CONFIG } from '../api/config';

interface AuthRedirectOptions {
  redirectIfAuthed?: boolean;
  preserveQueryParams?: boolean;
}

export function useAuthRedirect(
  redirectTo: string = AUTH_API_CONFIG.endpoints.LOGIN,
  options: AuthRedirectOptions = {}
) {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, isInitialized } = useAuthStatus();

  useEffect(() => {
    if (!isInitialized) return;

    const shouldRedirect = options.redirectIfAuthed 
      ? isAuthenticated 
      : !isAuthenticated;

    if (shouldRedirect) {
      const redirectPath = options.preserveQueryParams
        ? `${redirectTo}${location.search}`
        : redirectTo;

      navigate(redirectPath, {
        replace: true,
        state: { from: location.pathname }
      });
    }
  }, [isAuthenticated, isInitialized, redirectTo, location, navigate, options]);

  return { isAuthenticated, isInitialized };
}
