// auth/utils/authUtils.ts
import { jwtDecode } from 'jwt-decode';
import { tokenUtils } from '@/common/utils/token/tokenUtils';
import { storageUtils } from '@/common/utils/storage/storageUtils';
import type { AuthTokens, Permission } from '../types';
import type { User, UserRole } from '@/common/types/user';

const AUTH_STORAGE_KEY = 'auth_tokens';

interface AuthDecodedToken {
  sub: string;
  exp: number;
  roles: UserRole[];
  permissions: string[];
  email?: string;
  firstName?: string;
  lastName?: string;
}

export const authUtils = {
  getTokens(): AuthTokens | null {
    return storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
  },

  setTokens(tokens: AuthTokens, remember: boolean): void {
    storageUtils.setItem(AUTH_STORAGE_KEY, tokens, {
      storage: remember ? 'local' : 'session'
    });
  },

  clearTokens(): void {
    // Clear from both storages to ensure complete cleanup
    storageUtils.removeItem(AUTH_STORAGE_KEY, { storage: 'local' });
    storageUtils.removeItem(AUTH_STORAGE_KEY, { storage: 'session' });
  },

  getUserFromToken(token: string): Partial<User> | null {
    try {
      const decoded = jwtDecode<AuthDecodedToken>(token);
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

  checkPermission(userPermissions: Permission[], requiredPermission: Permission): boolean {
    return userPermissions.includes(requiredPermission);
  },

  checkPermissions(userPermissions: Permission[], requiredPermissions: Permission[]): boolean {
    return requiredPermissions.every(permission => 
      userPermissions.includes(permission)
    );
  },

  isTokenExpired(token: string): boolean {
    return tokenUtils.isTokenExpired(token);
  },

  createAuthHeader(token: string): string {
    return tokenUtils.createAuthHeader(token);
  },

  parseAuthHeader(header: string): string | null {
    return tokenUtils.parseAuthHeader(header);
  }
};

// Export types if needed by other modules
export type { AuthDecodedToken };