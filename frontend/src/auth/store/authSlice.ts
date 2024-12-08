// src/auth/store/authSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { AuthState, User, AuthTokens } from '../types/auth';

const initialState: AuthState = {
    user: null,
    status: 'unauthenticated',
    error: null,
    tokens: {
        accessToken: null,
        refreshToken: null
    }
};

const authSlice = createSlice({
    name: 'auth',
    initialState,
    reducers: {
        setUser(state, action: PayloadAction<User | null>) {
            state.user = action.payload;
            state.status = action.payload ? 'authenticated' : 'unauthenticated';
        },
        setTokens(state, action: PayloadAction<AuthTokens>) {
            state.tokens = {
                accessToken: action.payload.accessToken,
                refreshToken: action.payload.refreshToken
            };
        },
        setError(state, action: PayloadAction<string | null>) {
            state.error = action.payload;
        },
        setStatus(state, action: PayloadAction<AuthState['status']>) {
            state.status = action.payload;
        },
        setAuth(state, action: PayloadAction<{ user: User; tokens: AuthTokens }>) {
            state.user = action.payload.user;
            state.tokens = {
                accessToken: action.payload.tokens.accessToken,
                refreshToken: action.payload.tokens.refreshToken
            };
            state.status = 'authenticated';
            state.error = null;
        },
        clearAuth(state) {
            state.user = null;
            state.tokens = {
                accessToken: null,
                refreshToken: null
            };
            state.status = 'unauthenticated';
            state.error = null;
        }
    }
});

export const {
    setUser,
    setTokens,
    setError,
    setStatus,
    setAuth,
    clearAuth
} = authSlice.actions;

export default authSlice.reducer;


