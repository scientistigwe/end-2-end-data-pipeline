// src/auth/types/permissions.ts
export type ResourceType = 
  | 'users'
  | 'roles'
  | 'settings'
  | 'reports'
  | 'analytics'
  | 'audit'
  | 'profile';

export type ActionType = 
  | 'view'
  | 'create'
  | 'edit'
  | 'delete'
  | 'manage'
  | 'approve'
  | 'export';

// Format: action:resource
export type Permission =
  | `${ActionType}:${ResourceType}`
  | 'manage:admins'  // Special permission
  | 'manage:all';    // Super admin permission

export interface PermissionCheck {
  hasPermission: (permission: Permission) => boolean;
  hasAnyPermission: (permissions: Permission[]) => boolean;
  hasAllPermissions: (permissions: Permission[]) => boolean;
}

export const CORE_PERMISSIONS = {
  // User Management
  VIEW_USERS: 'view:users' as Permission,
  CREATE_USERS: 'create:users' as Permission,
  EDIT_USERS: 'edit:users' as Permission,
  DELETE_USERS: 'delete:users' as Permission,
  MANAGE_USERS: 'manage:users' as Permission,

  // Role Management
  VIEW_ROLES: 'view:roles' as Permission,
  MANAGE_ROLES: 'manage:roles' as Permission,

  // Admin Management
  MANAGE_ADMINS: 'manage:admins' as Permission,

  // Settings
  VIEW_SETTINGS: 'view:settings' as Permission,
  MANAGE_SETTINGS: 'manage:settings' as Permission,

  // Reports
  VIEW_REPORTS: 'view:reports' as Permission,
  CREATE_REPORTS: 'create:reports' as Permission,
  EXPORT_REPORTS: 'export:reports' as Permission,

  // Analytics
  VIEW_ANALYTICS: 'view:analytics' as Permission,

  // Audit
  VIEW_AUDIT: 'view:audit' as Permission,

  // Profile
  VIEW_PROFILE: 'view:profile' as Permission,
  EDIT_PROFILE: 'edit:profile' as Permission,

  // Super Admin
  MANAGE_ALL: 'manage:all' as Permission
} as const;

export const DEFAULT_PERMISSIONS: Record<string, Permission[]> = {
  admin: [
    CORE_PERMISSIONS.MANAGE_ALL
  ],
  manager: [
    CORE_PERMISSIONS.VIEW_USERS,
    CORE_PERMISSIONS.MANAGE_USERS,
    CORE_PERMISSIONS.VIEW_REPORTS,
    CORE_PERMISSIONS.VIEW_ANALYTICS,
    CORE_PERMISSIONS.VIEW_AUDIT
  ],
  user: [
    CORE_PERMISSIONS.VIEW_PROFILE,
    CORE_PERMISSIONS.EDIT_PROFILE
  ]
} as const;

export function isValidPermission(permission: string): permission is Permission {
  const [action, resource] = permission.split(':');
  if (!action || !resource) return false;

  const validActions = ['view', 'create', 'edit', 'delete', 'manage', 'approve', 'export'];
  const validResources = ['users', 'roles', 'settings', 'reports', 'analytics', 'audit', 'profile', 'admins', 'all'];

  return validActions.includes(action) && validResources.includes(resource);
}

export function formatPermission(permission: Permission): string {
  const [action, resource] = permission.split(':');
  return `${action.charAt(0).toUpperCase() + action.slice(1)} ${resource}`;
}

export function getRequiredPermissionsForRoute(route: string): Permission[] {
  const routePermissionsMap: Record<string, Permission[]> = {
    '/users': [CORE_PERMISSIONS.VIEW_USERS],
    '/users/create': [CORE_PERMISSIONS.CREATE_USERS],
    '/roles': [CORE_PERMISSIONS.VIEW_ROLES],
    '/settings': [CORE_PERMISSIONS.VIEW_SETTINGS],
    '/reports': [CORE_PERMISSIONS.VIEW_REPORTS],
    '/analytics': [CORE_PERMISSIONS.VIEW_ANALYTICS],
    '/audit': [CORE_PERMISSIONS.VIEW_AUDIT],
    '/profile': [CORE_PERMISSIONS.VIEW_PROFILE]
  };

  return routePermissionsMap[route] || [];
}