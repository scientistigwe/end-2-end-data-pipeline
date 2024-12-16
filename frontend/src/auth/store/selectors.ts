// src/auth/store/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '@/store/types';
import type { User } from '@/common/types/user';
import type { AuthState, AuthStatus, AuthTokens } from '../types';

// Base selectors with proper typing and null checks
export const selectAuthState = (state: RootState): AuthState => 
  state.auth;

export const selectUser = (state: RootState): User | null => 
  state.auth?.user || null;

export const selectAuthStatus = (state: RootState): AuthStatus => 
  state.auth?.status || 'unauthenticated';

export const selectAuthError = (state: RootState): string | null => 
  state.auth?.error || null;

export const selectAuthTokens = (state: RootState): AuthTokens => 
  state.auth?.tokens || { accessToken: null, refreshToken: null, expiresIn: null };

export const selectIsLoading = (state: RootState): boolean => 
  state.auth?.isLoading || false;

export const selectIsInitialized = (state: RootState): boolean => 
  state.auth?.initialized || false;

// Derived selectors with proper typing
export const selectIsAuthenticated = createSelector(
  selectAuthStatus,
  (status): boolean => status === 'authenticated'
);

export const selectUserEmail = createSelector(
  selectUser,
  (user): string | undefined => user?.email
);

export const selectUserName = createSelector(
  selectUser,
  (user): string | undefined => 
    user ? `${user.firstName} ${user.lastName}`.trim() || undefined : undefined
);

export const selectUserRole = createSelector(
  selectUser,
  (user) => user?.role || null
);

export const selectUserPermissions = createSelector(
  selectUser,
  (user): string[] => user?.permissions || []
);

// Token validation selectors
export const selectHasValidToken = createSelector(
  selectAuthTokens,
  (tokens): boolean => Boolean(tokens.accessToken && tokens.refreshToken)
);

export const selectIsSessionExpired = createSelector(
  selectAuthTokens,
  (tokens): boolean => tokens.expiresIn ? Date.now() > tokens.expiresIn : true
);

// Composite selectors
export const selectAuthenticatedUser = createSelector(
  [selectIsAuthenticated, selectUser],
  (isAuthenticated, user): User | null => isAuthenticated ? user : null
);

export const selectAuthenticationState = createSelector(
  [selectIsAuthenticated, selectIsLoading, selectAuthError],
  (isAuthenticated, isLoading, error): {
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
  } => ({
    isAuthenticated,
    isLoading,
    error
  })
);

// User info selectors
export const selectUserInfo = createSelector(
  selectUser,
  (user): {
    email?: string;
    fullName?: string;
    role?: string;
    permissions: string[];
  } => ({
    email: user?.email,
    fullName: user ? `${user.firstName} ${user.lastName}`.trim() : undefined,
    role: user?.role,
    permissions: user?.permissions || []
  })
);

// Token state selectors
export const selectTokenState = createSelector(
  [selectAuthTokens, selectIsSessionExpired],
  (tokens, isExpired): {
    hasToken: boolean;
    isExpired: boolean;
    expiresIn: number | null;
  } => ({
    hasToken: Boolean(tokens.accessToken),
    isExpired,
    expiresIn: tokens.expiresIn
  })
);