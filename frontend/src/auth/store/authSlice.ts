// src/auth/store/authSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { AuthState, AuthStatus } from '../types';
import type { User } from '@/common/types/user';

// Check for persisted auth data
function getPersistedAuth(): Partial<AuthState> {
  try {
    // Check for cookie-based authentication
    const hasAuthCookie = document.cookie.includes('refresh_token') || 
                        document.cookie.includes('access_token');
    
    // Check for user data in sessionStorage (optional)
    const persistedUser = sessionStorage.getItem('authUser');
    
    if (hasAuthCookie) {
      return {
        status: 'authenticated' as AuthStatus,
        isLoading: false,
        initialized: true,
        user: persistedUser ? JSON.parse(persistedUser) : null
      };
    }
  } catch (error) {
    console.error('Error checking persisted auth:', error);
  }
  
  return {};
}

const initialState: AuthState = {
    user: null,
    status: 'unauthenticated',
    error: null,
    isLoading: false,
    initialized: false
};

// Apply persisted data to initial state
const persistedAuth = getPersistedAuth();
const authInitialState = {
  ...initialState,
  ...persistedAuth,
};

const authSlice = createSlice({
    name: 'auth',
    initialState: authInitialState,
    reducers: {
        setUser(state, action: PayloadAction<User | null>) {
            state.user = action.payload;
            state.status = action.payload ? 'authenticated' : 'unauthenticated';
            state.error = null;
            
            // Persist user when it's set
            if (action.payload) {
                try {
                    sessionStorage.setItem('authUser', JSON.stringify(action.payload));
                } catch (error) {
                    console.error('Failed to persist user data:', error);
                }
            } else {
                sessionStorage.removeItem('authUser');
            }
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
            
            // Persist user
            try {
                sessionStorage.setItem('authUser', JSON.stringify(action.payload.user));
            } catch (error) {
                console.error('Failed to persist user data:', error);
            }
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
            
            // Persist user
            try {
                sessionStorage.setItem('authUser', JSON.stringify(action.payload.user));
            } catch (error) {
                console.error('Failed to persist user data:', error);
            }
        },
        
        authFailure(state, action: PayloadAction<string>) {
            state.status = 'unauthenticated';
            state.error = action.payload;
            state.isLoading = false;
            state.user = null;
            
            // Clear persisted data
            sessionStorage.removeItem('authUser');
        },
        
        clearAuth(state) {
            // Clear persisted data
            sessionStorage.removeItem('authUser');
            
            return {
                ...initialState,
                initialized: state.initialized // Preserve initialization state
            };
        },
        
        resetAuthState() {
            // Clear persisted data
            sessionStorage.removeItem('authUser');
            
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