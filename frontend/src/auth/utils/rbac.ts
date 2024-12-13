// auth/utils/rbac.ts
import type { RolePermissions, RoleHierarchy, RoleType } from '../types';
import { 
  Permission, 
  CORE_PERMISSIONS, 
  ACTION_TYPES, 
  RESOURCE_TYPES,
  isValidPermission 
} from '../types/permissions';

export const ROLE_HIERARCHY: RoleHierarchy = {
  admin: ['admin', 'manager', 'user'],
  manager: ['manager', 'user'],
  user: ['user']
} as const;

export const ROLE_PERMISSIONS: RolePermissions = {
  admin: [
    CORE_PERMISSIONS.VIEW_USERS,
    CORE_PERMISSIONS.MANAGE_USERS,
    CORE_PERMISSIONS.MANAGE_ROLES,
    CORE_PERMISSIONS.MANAGE_SYSTEM,
    CORE_PERMISSIONS.DELETE_USERS,
    CORE_PERMISSIONS.MANAGE_SETTINGS,
    CORE_PERMISSIONS.MANAGE_ALL
  ],
  manager: [
    CORE_PERMISSIONS.VIEW_USERS,
    CORE_PERMISSIONS.MANAGE_USERS,
    CORE_PERMISSIONS.VIEW_SETTINGS
  ],
  user: [
    CORE_PERMISSIONS.VIEW_PROFILE,
    CORE_PERMISSIONS.EDIT_PROFILE
  ]
} as const;

export const rbacUtils = {
  isValidRole(role: unknown): role is RoleType {
    return typeof role === 'string' && Object.keys(ROLE_HIERARCHY).includes(role);
  },

  isValidPermission,

  checkRoleHierarchy(userRole: RoleType, requiredRole: RoleType): boolean {
    return ROLE_HIERARCHY[userRole]?.includes(requiredRole) ?? false;
  },

  getRolePermissions(role: RoleType): Permission[] {
    const permissions = [...ROLE_PERMISSIONS[role]];
    if (permissions.includes(CORE_PERMISSIONS.MANAGE_ALL)) {
      // If has MANAGE_ALL, add all possible permissions
      return Object.values(ACTION_TYPES).flatMap(action =>
        Object.values(RESOURCE_TYPES).map(resource =>
          `${action}:${resource}` as Permission
        )
      );
    }
    return permissions;
  },

  hasPermission(role: RoleType, permission: Permission): boolean {
    const permissions = this.getRolePermissions(role);
    return permissions.includes(permission) || 
           permissions.includes(CORE_PERMISSIONS.MANAGE_ALL) ||
           this.hasWildcardPermission(permissions, permission);
  },

  hasWildcardPermission(userPermissions: Permission[], requiredPermission: Permission): boolean {
    const [reqAction, reqResource] = requiredPermission.split(':');
    return userPermissions.some(permission => {
      const [action, resource] = permission.split(':');
      return (action === ACTION_TYPES.ALL || action === reqAction) &&
             (resource === RESOURCE_TYPES.ALL || resource === reqResource);
    });
  },

  getRolesWithPermission(permission: Permission): RoleType[] {
    return (Object.entries(ROLE_PERMISSIONS) as [RoleType, Permission[]][])
      .filter(([_, permissions]) => 
        permissions.includes(permission) || 
        permissions.includes(CORE_PERMISSIONS.MANAGE_ALL)
      )
      .map(([role]) => role);
  },

  isRoleSuperiorTo(role1: RoleType, role2: RoleType): boolean {
    return this.checkRoleHierarchy(role1, role2) && role1 !== role2;
  },

  getCombinedPermissions(roles: RoleType[]): Permission[] {
    const allPermissions = roles.flatMap(role => this.getRolePermissions(role));
    return [...new Set(allPermissions)];
  }
};