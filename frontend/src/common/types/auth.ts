// common/types/auth.ts
// These are core types that other modules might need
export type BasePermission = {
    id: string;
    name: string;
    description?: string;
  };
  
  export type BaseRole = {
    id: string;
    name: string;
    description?: string;
    createdAt: string;
    updatedAt: string;
  };
  
  // For use across modules that need to check permissions
  export interface BasePermissionCheck {
    hasPermission: (permission: string) => boolean;
    hasAnyPermission: (permissions: string[]) => boolean;
    hasAllPermissions: (permissions: string[]) => boolean;
  }
  
  // Common auth interfaces for use in different modules
  export interface BaseAuthError {
    code: string;
    message: string;
    status: number;
  }
  
  // User session info needed across modules
  export interface BaseSessionInfo {
    isActive: boolean;
    lastActive: string;
    expiresAt?: string;
  }