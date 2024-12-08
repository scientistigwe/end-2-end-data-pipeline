// src/utils/session.ts
import { jwtDecode } from 'jwt-decode';
import { AuthTokens, User, RoleType } from '../types/auth';

interface DecodedToken {
  exp: number;
  sub: string;
  roles: RoleType[];
  permissions: string[];
}

class SessionManager {
  private static instance: SessionManager;
  private readonly TOKEN_KEY = 'auth_tokens';
  private readonly SESSION_TIMEOUT = 14 * 60 * 1000; // 14 minutes
  private refreshTimer: NodeJS.Timeout | null = null;

  private constructor() {
    // Private constructor to force singleton usage
  }

  static getInstance(): SessionManager {
    if (!SessionManager.instance) {
      SessionManager.instance = new SessionManager();
    }
    return SessionManager.instance;
  }

  storeTokens(tokens: AuthTokens): void {
    localStorage.setItem(this.TOKEN_KEY, JSON.stringify(tokens));
    this.setupRefreshTimer();
  }

  getTokens(): AuthTokens | null {
    const tokens = localStorage.getItem(this.TOKEN_KEY);
    return tokens ? JSON.parse(tokens) : null;
  }

  clearTokens(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }
  }

  getAccessToken(): string | null {
    const tokens = this.getTokens();
    return tokens?.accessToken ?? null;
  }

  isTokenExpired(): boolean {
    const decoded = this.getDecodedToken();
    if (!decoded) return true;
    return Date.now() >= decoded.exp * 1000;
  }

  getUserFromToken(): Partial<User> | null {
    const decoded = this.getDecodedToken();
    if (!decoded) return null;
    
    const role = decoded.roles[0];
    if (!role) return null;

    return {
      id: decoded.sub,
      permissions: decoded.permissions,
      role: role // This is now properly typed as RoleType
    };
  }

  private getDecodedToken(): DecodedToken | null {
    const token = this.getAccessToken();
    if (!token) return null;
    
    try {
      return jwtDecode<DecodedToken>(token);
    } catch {
      return null;
    }
  }

  private setupRefreshTimer(): void {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }

    this.refreshTimer = setInterval(() => {
      // Emit refresh token event
      window.dispatchEvent(new CustomEvent('token:refresh'));
    }, this.SESSION_TIMEOUT);
  }

  isAuthenticated(): boolean {
    return !this.isTokenExpired();
  }
}

export const sessionManager = SessionManager.getInstance();

