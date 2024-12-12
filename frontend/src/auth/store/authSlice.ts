// src/auth/store/authSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { AuthState, AuthTokens, AuthStatus } from '../types/auth';
import type { User } from '@/common/types/user';

const initialState: AuthState = {
    user: null,
    isLoading: null,
    status: 'unauthenticated',
    error: null,
    tokens: {
        accessToken: null,
        refreshToken: null,
        expiresIn: null
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
            state.tokens = action.payload;
        },
        setError(state, action: PayloadAction<string | null>) {
            state.error = action.payload;
        },
        setStatus(state, action: PayloadAction<AuthStatus>) {
            state.status = action.payload;
        },
        setAuth(state, action: PayloadAction<{ user: User; tokens: AuthTokens }>) {
            state.user = action.payload.user;
            state.tokens = action.payload.tokens;
            state.status = 'authenticated';
            state.error = null;
        },
        clearAuth(state) {
            state.user = null;
            state.tokens = {
                accessToken: null,
                refreshToken: null,
                expiresIn: null
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

export type authState = typeof initialState;
export default authSlice.reducer;