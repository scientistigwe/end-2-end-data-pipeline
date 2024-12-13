// auth/store/authSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { AuthState, AuthTokens, AuthStatus } from '../types';
import type { User } from '@/common/types/user';

const initialState: AuthState = {
    user: null,
    status: 'unauthenticated',
    error: null,
    tokens: {
        accessToken: null,
        refreshToken: null,
        expiresIn: null
    },
    isLoading: false,
    initialized: false
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
            state.isLoading = false;
        },
        setStatus(state, action: PayloadAction<AuthStatus>) {
            state.status = action.payload;
        },
        setLoading(state, action: PayloadAction<boolean>) {
            state.isLoading = action.payload;
        },
        setInitialized(state, action: PayloadAction<boolean>) {
            state.initialized = action.payload;
        },
        setAuth(state, action: PayloadAction<{ user: User; tokens: AuthTokens }>) {
            state.user = action.payload.user;
            state.tokens = action.payload.tokens;
            state.status = 'authenticated';
            state.error = null;
            state.isLoading = false;
        },
        clearAuth(state) {
            return {
                ...initialState,
                initialized: state.initialized
            };
        }
    }
});

export const {
    setUser,
    setTokens,
    setError,
    setStatus,
    setLoading,
    setInitialized,
    setAuth,
    clearAuth
} = authSlice.actions;

export default authSlice.reducer;