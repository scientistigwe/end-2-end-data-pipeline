// auth/store/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '@/store/types';
import type { User } from '@/common/types/user';
import type { AuthState } from '../types';

// Base selectors
export const selectAuthState = (state: RootState): AuthState => state.auth;

export const selectUser = createSelector(
    selectAuthState,
    (auth): User | null => auth.user
);

export const selectAuthStatus = createSelector(
    selectAuthState,
    (auth) => auth.status
);

export const selectAuthError = createSelector(
    selectAuthState,
    (auth) => auth.error
);

export const selectAuthTokens = createSelector(
    selectAuthState,
    (auth) => auth.tokens
);

export const selectIsLoading = createSelector(
    selectAuthState,
    (auth) => auth.isLoading
);

export const selectIsInitialized = createSelector(
    selectAuthState,
    (auth) => auth.initialized
);

// Derived selectors
export const selectIsAuthenticated = createSelector(
    selectAuthStatus,
    (status) => status === 'authenticated'
);

export const selectUserEmail = createSelector(
    selectUser,
    (user): string | undefined => user?.email
);

export const selectUserName = createSelector(
    selectUser,
    (user): string | undefined => user ? `${user.firstName} ${user.lastName}` : undefined
);

export const selectUserRole = createSelector(
    selectUser,
    (user) => user?.role
);

export const selectUserPermissions = createSelector(
    selectUser,
    (user) => user?.permissions ?? []
);

// Authentication state checks
export const selectHasValidToken = createSelector(
    selectAuthTokens,
    (tokens) => !!tokens.accessToken && !!tokens.refreshToken
);

export const selectIsSessionExpired = createSelector(
    selectAuthTokens,
    (tokens) => tokens.expiresIn ? Date.now() > tokens.expiresIn : true
);

// Combined selectors
export const selectAuthenticatedUser = createSelector(
    [selectIsAuthenticated, selectUser],
    (isAuthenticated, user) => isAuthenticated ? user : null
);

export const selectAuthenticationState = createSelector(
    [selectIsAuthenticated, selectIsLoading, selectAuthError],
    (isAuthenticated, isLoading, error) => ({
        isAuthenticated,
        isLoading,
        error
    })
);