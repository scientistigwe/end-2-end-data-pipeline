// auth/api/config.ts
export const AUTH_API_CONFIG = {
  baseURL: '/api/v1/auth',
  timeout: 30000,
  endpoints: {
    LOGIN: '/login',
    REGISTER: '/register',
    LOGOUT: '/logout',
    REFRESH: '/refresh',
    VERIFY_EMAIL: '/verify-email',
    FORGOT_PASSWORD: '/forgot-password',
    RESET_PASSWORD: '/reset-password',
    PROFILE: '/profile',
    CHANGE_PASSWORD: '/profile/change-password'
  }
} as const;
