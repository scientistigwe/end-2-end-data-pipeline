// src/services/api/authUtils.ts
import type { AuthTokens } from '../types/auth';

const TOKEN_KEY = 'auth_tokens';

export const authUtils = {
  setTokens(tokens: AuthTokens): void {
    localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
  },

  getTokens(): AuthTokens | null {
    const tokens = localStorage.getItem(TOKEN_KEY);
    return tokens ? JSON.parse(tokens) : null;
  },

  clearTokens(): void {
    localStorage.removeItem(TOKEN_KEY);
  },

  isTokenExpired(token: string): boolean {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return Date.now() >= payload.exp * 1000;
    } catch {
      return true;
    }
  }
};