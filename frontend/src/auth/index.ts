// src/auth/index.ts
export * from './api/authClient';
export * from './hooks/useAuth';
export * from './hooks/useSession';
export * from './store/authSlice';
export * from './store/selectors';
export * from './types/auth';
export * from './hooks/usePermissions';
export * from './components/PermissionGuard';
export type { Permission } from './types/permissions';

// auth/index.ts
export { AuthService } from './services';
export { authApi } from './api';
export { useAuth, useAuthRedirect, usePermissions } from './hooks';
export { AuthProvider } from './providers';
export * from './types';
export { AUTH_ROUTES, AUTH_PASSWORD_POLICY, AUTH_ROLES, AUTH_STORAGE } from './constants';