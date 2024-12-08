// src/auth/api/config.ts
export const AUTH_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_URL || '/api/v1',
  TIMEOUT: 30000,
  ENDPOINTS: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    REFRESH: '/auth/refresh',
    LOGOUT: '/auth/logout',
    VERIFY: '/auth/verify',
    FORGOT_PASSWORD: '/auth/forgot-password',
    RESET_PASSWORD: '/auth/reset-password',
    VERIFY_EMAIL: '/auth/verify-email',
    PROFILE: '/auth/profile',
    CHANGE_PASSWORD: '/auth/change-password'
  }
} as const;

