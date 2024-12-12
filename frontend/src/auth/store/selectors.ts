// src/auth/store/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '@/store/rootReducer';

export const selectAuthState = (state: RootState) => state.auth;
export const selectUser = (state: RootState) => state.auth.user;
export const selectAuthStatus = (state: RootState) => state.auth.status;
export const selectAuthError = (state: RootState) => state.auth.error;
export const selectAuthTokens = (state: RootState) => state.auth.tokens;

export const selectIsAuthenticated = createSelector(
    selectAuthStatus,
    status => status === 'authenticated'
);

export const selectUserRole = createSelector(
    selectUser,
    user => user?.role
);

export const selectUserPermissions = createSelector(
    selectUser,
    user => user?.permissions ?? []
);
