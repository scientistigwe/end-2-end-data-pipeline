// auth/utils/formatters.ts
import type { User } from '@/common/types/user';
import { dateUtils } from '@/common/utils/date/dateUtils';

// Error message mapping in closure scope
const ERROR_MESSAGES: Record<string, string> = {
  invalid_credentials: 'Invalid email or password',
  account_locked: 'Account is locked. Please contact support',
  email_not_verified: 'Please verify your email address',
  token_expired: 'Your session has expired. Please login again',
  invalid_token: 'Invalid authentication token',
  password_mismatch: 'Passwords do not match',
  weak_password: 'Password does not meet security requirements'
};

export const authFormatters = {
  formatFullName(user: Partial<User>): string {
    if (!user.firstName && !user.lastName) return 'N/A';
    return `${user.firstName || ''} ${user.lastName || ''}`.trim();
  },

  formatInitials(user: Partial<User>): string {
    const first = user.firstName?.[0] || '';
    const last = user.lastName?.[0] || '';
    return (first + last).toUpperCase();
  },

  formatLastLogin(lastLogin?: string): string {
    if (!lastLogin) return 'Never';
    return dateUtils.formatRelativeTime(lastLogin);
  },

  formatRole(role?: string): string {
    if (!role) return 'N/A';
    return role.charAt(0).toUpperCase() + role.slice(1).toLowerCase();
  },

  formatPermissions(permissions: string[]): string {
    return permissions
      .map(p => p.split(':')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
      )
      .join(', ');
  },

  formatAuthError(error: unknown): string {
    if (typeof error === 'string') return error;
    
    if (error instanceof Error) {
      return ERROR_MESSAGES[error.message] || error.message;
    }
    
    if (typeof error === 'object' && error !== null) {
      const message = (error as any).response?.data?.message || (error as any).message;
      return ERROR_MESSAGES[message] || message || 'An error occurred during authentication';
    }

    return 'An unexpected error occurred';
  },

  formatSessionStatus(expiresAt?: number): string {
    if (!expiresAt) return 'Inactive';
    const now = Date.now();
    if (expiresAt < now) return 'Expired';
    return 'Active';
  },

  formatUserStatus(isActive?: boolean, isVerified?: boolean): string {
    if (!isActive) return 'Inactive';
    if (!isVerified) return 'Unverified';
    return 'Active';
  }
};

// Type for use in components
export type AuthFormatters = typeof authFormatters;

