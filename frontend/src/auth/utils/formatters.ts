// src/auth/utils/formatters.ts
import type { User } from '../types/auth';

export const formatters = {
  /**
   * Format user's full name
   */
  formatFullName(user: Partial<User>): string {
    if (!user.firstName && !user.lastName) return 'N/A';
    return `${user.firstName || ''} ${user.lastName || ''}`.trim();
  },

  /**
   * Format user's initials
   */
  formatInitials(user: Partial<User>): string {
    const first = user.firstName?.[0] || '';
    const last = user.lastName?.[0] || '';
    return (first + last).toUpperCase();
  },

  /**
   * Format last login time
   */
  formatLastLogin(lastLogin?: string): string {
    if (!lastLogin) return 'Never';
    
    const date = new Date(lastLogin);
    const now = new Date();
    const diffInHours = Math.abs(now.getTime() - date.getTime()) / 36e5;

    if (diffInHours < 24) {
      return `${Math.round(diffInHours)} hours ago`;
    }
    return date.toLocaleDateString();
  },

  /**
   * Format user role for display
   */
  formatRole(role?: string): string {
    if (!role) return 'N/A';
    return role.charAt(0).toUpperCase() + role.slice(1).toLowerCase();
  },

  /**
   * Format permissions for display
   */
  formatPermissions(permissions: string[]): string {
    return permissions
      .map(p => p.split(':')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
      )
      .join(', ');
  },

  /**
   * Format error messages
   */
  formatAuthError(error: any): string {
    if (typeof error === 'string') return error;
    
    const message = error.response?.data?.message || error.message;
    switch (message) {
      case 'invalid_credentials':
        return 'Invalid email or password';
      case 'account_locked':
        return 'Account is locked. Please contact support';
      case 'email_not_verified':
        return 'Please verify your email address';
      default:
        return message || 'An error occurred during authentication';
    }
  },

  /**
   * Format session duration
   */
  formatSessionDuration(expiresIn: number): string {
    const minutes = Math.floor(expiresIn / 60);
    if (minutes < 60) return `${minutes} minutes`;
    const hours = Math.floor(minutes / 60);
    return `${hours} hours`;
  }
};