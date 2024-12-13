// auth/hooks/useAuthStatus.ts
import { useSelector } from 'react-redux';
import { selectAuthenticationState, selectIsInitialized } from '../store/selectors';

export function useAuthStatus() {
  const { isAuthenticated, isLoading, error } = useSelector(selectAuthenticationState);
  const isInitialized = useSelector(selectIsInitialized);

  return {
    isInitialized,
    isAuthenticated,
    isLoading,
    error,
    status: isInitialized 
      ? (isAuthenticated ? 'authenticated' : 'unauthenticated') 
      : 'initializing'
  } as const;
}
