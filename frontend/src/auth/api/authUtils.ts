// auth/api/authUtils.ts
import { storageUtils } from '@/common/utils/storage/storageUtils';
import type { AuthTokens } from '../types';

const AUTH_STORAGE_KEY = 'auth_tokens';

export const authUtils = {
  /**
   * Sets the authentication tokens in storage
   */
  setTokens(tokens: AuthTokens): void {
    storageUtils.setItem(AUTH_STORAGE_KEY, tokens);
  },

  /**
   * Retrieves the authentication tokens from storage
   */
  getTokens(): AuthTokens | null {
    return storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
  },

  /**
   * Removes the authentication tokens from storage
   */
  clearTokens(): void {
    storageUtils.removeItem(AUTH_STORAGE_KEY);
  },

  /**
   * Checks if a token is expired
   */
  isTokenExpired(token: string): boolean {
    if (!token) return true;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return Date.now() >= payload.exp * 1000;
    } catch {
      return true;
    }
  },

  /**
   * Gets the payload from a JWT token
   */
  getTokenPayload<T>(token: string): T | null {
    try {
      return JSON.parse(atob(token.split('.')[1]));
    } catch {
      return null;
    }
  }
};