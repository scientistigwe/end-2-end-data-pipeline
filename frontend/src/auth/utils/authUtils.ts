// src/auth/utils/authUtils.ts
import { jwtDecode } from 'jwt-decode';
import type { User, AuthTokens, UserRole } from '../types/auth';

interface DecodedToken {
  sub: string;
  exp: number;
  roles: UserRole[];
  permissions: string[];
  email?: string;
  firstName?: string;
  lastName?: string;
}

export const AUTH_STORAGE_KEY = 'auth_tokens';

export const authUtils = {
  setTokens(tokens: AuthTokens): void {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(tokens));
  },

  getTokens(): AuthTokens | null {
    const tokens = localStorage.getItem(AUTH_STORAGE_KEY);
    return tokens ? JSON.parse(tokens) : null;
  },

  clearTokens(): void {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  },

  isTokenExpired(token: string): boolean {
    try {
      const decoded = jwtDecode<DecodedToken>(token);
      return (decoded.exp * 1000) <= Date.now() + 10000;
    } catch {
      return true;
    }
  },

  getUserFromToken(token: string): Partial<User> | null {
    try {
      const decoded = jwtDecode<DecodedToken>(token);
      
      // Ensure role is of type UserRole
      const role = decoded.roles[0];
      if (!this.isValidUserRole(role)) {
        throw new Error('Invalid role in token');
      }

      return {
        id: decoded.sub,
        role,
        permissions: decoded.permissions,
        email: decoded.email,
        firstName: decoded.firstName,
        lastName: decoded.lastName
      };
    } catch {
      return null;
    }
  },

  isValidUserRole(role: string): role is UserRole {
    return ['admin', 'manager', 'user'].includes(role);
  },

  isRefreshTokenValid(token: string): boolean {
    try {
      const decoded = jwtDecode<DecodedToken>(token);
      return (decoded.exp * 1000) > Date.now() + 60000;
    } catch {
      return false;
    }
  },

  parseAuthHeader(header: string): string | null {
    if (!header || !header.startsWith('Bearer ')) {
      return null;
    }
    return header.substring(7);
  },

  createAuthHeader(token: string): string {
    return `Bearer ${token}`;
  },

  persistSession(tokens: AuthTokens, remember: boolean = false): void {
    if (remember) {
      this.setTokens(tokens);
    } else {
      sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(tokens));
    }
  },

  clearSession(): void {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    sessionStorage.removeItem(AUTH_STORAGE_KEY);
  },

  // Type guard for AuthTokens
  isAuthTokens(obj: unknown): obj is AuthTokens {
    return (
      typeof obj === 'object' &&
      obj !== null &&
      'accessToken' in obj &&
      'refreshToken' in obj &&
      'expiresIn' in obj
    );
  },

  // Validate token format without decoding
  isValidTokenFormat(token: string): boolean {
    const parts = token.split('.');
    return parts.length === 3 && parts.every(part => part.length > 0);
  }
};