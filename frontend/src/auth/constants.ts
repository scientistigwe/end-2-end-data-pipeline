// auth/constants.ts
export const AUTH_ROUTES = {
  LOGIN: '/auth/login',
  REGISTER: '/auth/register',
  FORGOT_PASSWORD: '/auth/forgot-password',
  RESET_PASSWORD: '/auth/reset-password/:token',
  VERIFY_EMAIL: '/auth/verify-email/:token',
  PROFILE: '/auth/profile'
} as const;

export const AUTH_STORAGE = {
  TOKEN_KEY: 'auth_tokens',
  REFRESH_INTERVAL: 14 * 60 * 1000, // 14 minutes
} as const;

export const AUTH_PASSWORD_POLICY = {
  minLength: 8,
  requireUppercase: true,
  requireLowercase: true,
  requireNumbers: true,
  requireSpecialChars: true
} as const;

export const AUTH_ROLES = {
  ADMIN: 'admin',
  USER: 'user'
} as const;