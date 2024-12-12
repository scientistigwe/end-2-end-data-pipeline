// auth/types/permissions.ts
// Core permission types as const objects
export const RESOURCE_TYPES = {
  USERS: 'users',
  ROLES: 'roles',
  PROFILE: 'profile',
  SYSTEM: 'system',
  SETTINGS: 'settings'
} as const;

export const ACTION_TYPES = {
  VIEW: 'view',
  CREATE: 'create',
  EDIT: 'edit',
  DELETE: 'delete',
  MANAGE: 'manage'
} as const;

// Derive types from const objects
export type ResourceType = typeof RESOURCE_TYPES[keyof typeof RESOURCE_TYPES];
export type ActionType = typeof ACTION_TYPES[keyof typeof ACTION_TYPES];

// Format: action:resource
export type Permission = `${ActionType}:${ResourceType}`;

// Permission checking interface
export interface PermissionCheck {
  hasPermission: (permission: Permission) => boolean;
  hasAnyPermission: (permissions: Permission[]) => boolean;
  hasAllPermissions: (permissions: Permission[]) => boolean;
}

// Core auth permissions
export const CORE_PERMISSIONS = {
  // User Management
  VIEW_USERS: `${ACTION_TYPES.VIEW}:${RESOURCE_TYPES.USERS}` as Permission,
  CREATE_USERS: `${ACTION_TYPES.CREATE}:${RESOURCE_TYPES.USERS}` as Permission,
  EDIT_USERS: `${ACTION_TYPES.EDIT}:${RESOURCE_TYPES.USERS}` as Permission,
  DELETE_USERS: `${ACTION_TYPES.DELETE}:${RESOURCE_TYPES.USERS}` as Permission,
  MANAGE_USERS: `${ACTION_TYPES.MANAGE}:${RESOURCE_TYPES.USERS}` as Permission,

  // Role Management
  VIEW_ROLES: `${ACTION_TYPES.VIEW}:${RESOURCE_TYPES.ROLES}` as Permission,
  MANAGE_ROLES: `${ACTION_TYPES.MANAGE}:${RESOURCE_TYPES.ROLES}` as Permission,

  // System Level
  MANAGE_SYSTEM: `${ACTION_TYPES.MANAGE}:${RESOURCE_TYPES.SYSTEM}` as Permission,

  // Settings
  VIEW_SETTINGS: `${ACTION_TYPES.VIEW}:${RESOURCE_TYPES.SETTINGS}` as Permission,
  MANAGE_SETTINGS: `${ACTION_TYPES.MANAGE}:${RESOURCE_TYPES.SETTINGS}` as Permission,

  // Profile
  VIEW_PROFILE: `${ACTION_TYPES.VIEW}:${RESOURCE_TYPES.PROFILE}` as Permission,
  EDIT_PROFILE: `${ACTION_TYPES.EDIT}:${RESOURCE_TYPES.PROFILE}` as Permission,
} as const;

// Helper functions
export function isValidPermission(permission: string): permission is Permission {
  const [action, resource] = permission.split(':');
  if (!action || !resource) return false;
  
  return (
    Object.values(ACTION_TYPES).includes(action as ActionType) &&
    Object.values(RESOURCE_TYPES).includes(resource as ResourceType)
  );
}

export function formatPermission(permission: Permission): string {
  const [action, resource] = permission.split(':');
  return `${action.charAt(0).toUpperCase() + action.slice(1)} ${resource}`;
}