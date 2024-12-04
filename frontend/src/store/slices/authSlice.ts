// store/slices/authSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { RootState } from '../index';

// Define user interface instead of using 'any'
interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user' | 'manager';
  permissions: string[];
  lastLogin?: string;
}

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  sessionExpiry?: string;
}

export interface AuthPayload {
  token: string;
  refreshToken: string;
  user: User;
  sessionExpiry?: string;
}

interface UpdateUserPayload {
  name?: string;
  email?: string;
  role?: 'admin' | 'user' | 'manager';
  permissions?: string[];
}

const initialState: AuthState = {
  token: null,
  refreshToken: null,
  user: null,
  isAuthenticated: false,
  loading: false,
  error: null,
  sessionExpiry: undefined
};

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    loginStart: (state) => {
      state.loading = true;
      state.error = null;
    },
    setAuth: (state, action: PayloadAction<AuthPayload>) => {
      state.token = action.payload.token;
      state.refreshToken = action.payload.refreshToken;
      state.user = action.payload.user;
      state.isAuthenticated = true;
      state.loading = false;
      state.error = null;
      state.sessionExpiry = action.payload.sessionExpiry;
    },
    updateUser: (state, action: PayloadAction<UpdateUserPayload>) => {
      if (state.user) {
        state.user = {
          ...state.user,
          ...action.payload,
        };
      }
    },
    setError: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
      state.loading = false;
    },
    clearAuth: (state) => {
      state.token = null;
      state.refreshToken = null;
      state.user = null;
      state.isAuthenticated = false;
    },
    refreshToken: (state, action: PayloadAction<{ token: string; refreshToken: string }>) => {
      state.token = action.payload.token;
      state.refreshToken = action.payload.refreshToken;
    }
  }
});

// Selectors
export const selectIsAuthenticated = (state: RootState) => state.auth.isAuthenticated;
export const selectUser = (state: RootState) => state.auth.user;
export const selectToken = (state: RootState) => state.auth.token;
export const selectAuthLoading = (state: RootState) => state.auth.loading;
export const selectAuthError = (state: RootState) => state.auth.error;
export const selectSessionExpiry = (state: RootState) => state.auth.sessionExpiry;
export const selectIsAdmin = (state: RootState) => state.auth.user?.role === 'admin';
export const selectUserPermissions = (state: RootState) => state.auth.user?.permissions ?? [];

// Custom selector to check specific permissions
export const hasPermission = (permission: string) => (state: RootState) => 
  state.auth.user?.permissions.includes(permission) ?? false;

export const { 
  setAuth, 
  clearAuth, 
  updateUser, 
  loginStart, 
  setError,
  refreshToken 
} = authSlice.actions;

export default authSlice.reducer;