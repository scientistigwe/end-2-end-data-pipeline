// src/auth/store/authSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { AuthState, AuthStatus } from '../types';
import type { User } from '@/common/types/user';

const initialState: AuthState = {
    user: null,
    status: 'unauthenticated',
    error: null,
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
            state.error = null;
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
        
        setAuth(state, action: PayloadAction<{ user: User }>) {
            state.user = action.payload.user;
            state.status = 'authenticated';
            state.error = null;
            state.isLoading = false;
        },
        
        startAuthRequest(state) {
            state.isLoading = true;
            state.error = null;
        },
        
        endAuthRequest(state) {
            state.isLoading = false;
        },
        
        authSuccess(state, action: PayloadAction<{ user: User }>) {
            state.user = action.payload.user;
            state.status = 'authenticated';
            state.error = null;
            state.isLoading = false;
        },
        
        authFailure(state, action: PayloadAction<string>) {
            state.status = 'unauthenticated';
            state.error = action.payload;
            state.isLoading = false;
            state.user = null;
        },
        
        clearAuth(state) {
            return {
                ...initialState,
                initialized: state.initialized // Preserve initialization state
            };
        },
        
        resetAuthState() {
            return initialState;
        }
    }
});

// Action creators
export const {
    setUser,
    setError,
    setStatus,
    setLoading,
    setInitialized,
    setAuth,
    startAuthRequest,
    endAuthRequest,
    authSuccess,
    authFailure,
    clearAuth,
    resetAuthState
} = authSlice.actions;

// Reducer
export default authSlice.reducer;
