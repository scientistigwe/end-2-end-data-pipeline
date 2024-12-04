// src/services/api/authApi.ts
import axios from 'axios';
import type { User } from './types';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000/api';

// Request interfaces
interface LoginCredentials {
  username: string;
  password: string;
}

interface RegisterData {
  username: string;
  email: string;
  password: string;
}

// Response interfaces
interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: User;  // Using shared User type
}

interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  user: User;  // Using shared User type
}

export const authApi = {
  login: (credentials: LoginCredentials) =>
    axios.post<AuthResponse>(`${API_URL}/auth/login`, credentials),

  register: (data: RegisterData) =>
    axios.post<AuthResponse>(`${API_URL}/auth/register`, data),

  refreshToken: (token: string) =>
    axios.post<RefreshTokenResponse>(`${API_URL}/auth/refresh`, { token }),

  verifyToken: (token: string) =>
    axios.post<RefreshTokenResponse>(`${API_URL}/auth/verify`, { token }),

  forgotPassword: (email: string) =>
    axios.post(`${API_URL}/auth/forgot-password`, { email }),

  resetPassword: (token: string, password: string) =>
    axios.post(`${API_URL}/auth/reset-password`, { token, password }),

  verifyEmail: (token: string) =>
    axios.post(`${API_URL}/auth/verify-email`, { token }),

  logout: () => axios.post(`${API_URL}/auth/logout`),
};

// Export types
export type {
  LoginCredentials,
  RegisterData,
  AuthResponse,
  RefreshTokenResponse
};