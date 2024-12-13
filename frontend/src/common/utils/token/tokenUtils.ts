// common/utils/token/tokenUtils.ts
import { jwtDecode } from 'jwt-decode';

interface BaseDecodedToken {
  sub: string;
  exp: number;
}

export const tokenUtils = {
  /**
   * Check if a token is expired
   * @param token JWT token
   * @returns boolean indicating if token is expired
   */
  isTokenExpired(token: string): boolean {
    if (!token) return true;
    try {
      const decoded = jwtDecode<BaseDecodedToken>(token);
      // Add 10 second buffer for clock skew
      return (decoded.exp * 1000) <= Date.now() + 10000;
    } catch {
      return true;
    }
  },

  /**
   * Validate token format (3 parts separated by dots)
   * @param token JWT token
   * @returns boolean indicating if token format is valid
   */
  isValidTokenFormat(token: string): boolean {
    if (!token) return false;
    const parts = token.split('.');
    return parts.length === 3 && parts.every(part => part.length > 0);
  },

  /**
   * Extract token from Authorization header
   * @param header Authorization header value
   * @returns token or null if invalid
   */
  parseAuthHeader(header: string): string | null {
    if (!header || !header.startsWith('Bearer ')) {
      return null;
    }
    return header.substring(7);
  },

  /**
   * Create Authorization header value
   * @param token JWT token
   * @returns formatted Authorization header value
   */
  createAuthHeader(token: string): string {
    return `Bearer ${token}`;
  },

  /**
   * Decode token payload without validation
   * @param token JWT token
   * @returns decoded token payload or null if invalid
   */
  decodeToken<T extends BaseDecodedToken>(token: string): T | null {
    try {
      return jwtDecode<T>(token);
    } catch {
      return null;
    }
  },

  /**
   * Get token expiration time in milliseconds
   * @param token JWT token
   * @returns expiration time in milliseconds or null if invalid
   */
  getTokenExpiration(token: string): number | null {
    try {
      const decoded = jwtDecode<BaseDecodedToken>(token);
      return decoded.exp * 1000;
    } catch {
      return null;
    }
  },

  /**
   * Calculate remaining valid time for token
   * @param token JWT token
   * @returns remaining time in milliseconds or 0 if expired/invalid
   */
  getTokenRemainingTime(token: string): number {
    const expiration = this.getTokenExpiration(token);
    if (!expiration) return 0;
    
    const remaining = expiration - Date.now();
    return remaining > 0 ? remaining : 0;
  }
};

// Export type for use in other modules
export type { BaseDecodedToken };