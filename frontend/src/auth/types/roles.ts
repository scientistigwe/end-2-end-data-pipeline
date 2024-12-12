// auth/types/roles.ts
export type RoleType = 'admin' | 'manager' | 'user';

export interface Role {
  id: string;
  name: RoleType;
  description?: string;
  permissions: string[];
  createdAt: string;
  updatedAt: string;
}

export interface RoleCreateData {
  name: RoleType;
  description?: string;
  permissions: string[];
}

export interface RoleUpdateData {
  name?: RoleType;
  description?: string;
  permissions?: string[];
}

// Track role assignments and changes
export interface RoleAudit {
  id: string;
  userId: string;
  oldRole?: string;
  newRole: string;
  changedBy: string;
  timestamp: string;
}

export interface RoleMutationResponse {
  success: boolean;
  message: string;
  role?: Role;
}