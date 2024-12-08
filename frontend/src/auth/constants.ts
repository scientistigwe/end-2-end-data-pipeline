// src/auth/constants.ts
export const AUTH_ROUTES = {
    LOGIN: '/login',
    REGISTER: '/register',
    FORGOT_PASSWORD: '/forgot-password',
    RESET_PASSWORD: '/reset-password/:token',
    VERIFY_EMAIL: '/verify-email/:token',
    PROFILE: '/profile'
  } as const;
  
  export const TOKEN_STORAGE_KEY = 'auth_tokens';
  export const REFRESH_TOKEN_INTERVAL = 14 * 60 * 1000; // 14 minutes
  
  export const PASSWORD_REQUIREMENTS = {
    minLength: 8,
    requireUppercase: true,
    requireLowercase: true,
    requireNumbers: true,
    requireSpecialChars: true
  } as const;
  
  export const USER_ROLES = {
    ADMIN: 'admin',
    MANAGER: 'manager',
    USER: 'user'
  } as const;
  
  export const USER_PERMISSIONS = {
    VIEW_USERS: 'view:users',
    MANAGE_USERS: 'manage:users',
    VIEW_SETTINGS: 'view:settings',
    MANAGE_SETTINGS: 'manage:settings'
  } as const;