// auth/store/authSlice.ts
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

// Selectors
export const selectAuth = (state: { auth: AuthState }) => state.auth;
export const selectUser = (state: { auth: AuthState }) => state.auth.user;
export const selectAuthStatus = (state: { auth: AuthState }) => state.auth.status;
export const selectAuthError = (state: { auth: AuthState }) => state.auth.error;
export const selectIsLoading = (state: { auth: AuthState }) => state.auth.isLoading;
export const selectIsInitialized = (state: { auth: AuthState }) => state.auth.initialized;
export const selectIsAuthenticated = (state: { auth: AuthState }) => 
    state.auth.status === 'authenticated' && !!state.auth.user;

// Thunks (if needed)
// export const loginThunk = createAsyncThunk(
//     'auth/login',
//     async (credentials: LoginCredentials, { dispatch }) => {
//         try {
//             dispatch(startAuthRequest());
//             const response = await authApi.login(credentials);
//             dispatch(authSuccess({ user: response.user }));
//             return response;
//         } catch (error) {
//             const message = error instanceof Error ? error.message : 'Login failed';
//             dispatch(authFailure(message));
//             throw error;
//         }
//     }
// );

// Reducer
export default authSlice.reducer;

// Types
export interface AuthState {
    user: User | null;
    status: AuthStatus;
    error: string | null;
    isLoading: boolean;
    initialized: boolean;
}