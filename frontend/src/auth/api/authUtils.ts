// auth/api/authUtils.ts
import { StorageUtils } from '@/common/api/utils/storage';
import { tokenUtils } from '@/common/api/utils/token';
import type { AuthTokens } from '../types';

const AUTH_STORAGE_KEY = 'auth_tokens';

export const authUtils = {
  setTokens(tokens: AuthTokens): void {
    StorageUtils.setItem(AUTH_STORAGE_KEY, tokens);
  },

  getTokens(): AuthTokens | null {
    return StorageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
  },

  clearTokens(): void {
    StorageUtils.removeItem(AUTH_STORAGE_KEY);
  },

  isTokenExpired: tokenUtils.isExpired
};