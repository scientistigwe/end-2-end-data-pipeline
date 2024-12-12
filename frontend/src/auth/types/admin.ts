// auth/types/admin.ts
import type { RoleType } from './roles';

// For bulk operations on users
export interface AdminBulkAction {
  type: 'delete' | 'updateRole' | 'suspend' | 'activate';
  userIds: string[];
  payload?: {
    roleId?: string;
    reason?: string;
  };
}

// For filtering users in admin views
export interface AdminUserFilters {
  role?: RoleType;
  status?: 'active' | 'inactive' | 'suspended';
  searchQuery?: string;
  dateRange?: {
    start: string;
    end: string;
  };
  sortBy?: 'name' | 'email' | 'role' | 'status' | 'createdAt';
  sortOrder?: 'asc' | 'desc';
}

// For pagination in admin views
export interface AdminPaginationParams {
  page: number;
  limit: number;
}

// For admin audit logs
export interface AdminAuditLog {
  id: string;
  action: string;
  performedBy: string;
  targetUser?: string;
  details: any;
  timestamp: string;
}

export interface AdminStats {
  totalUsers: number;
  activeUsers: number;
  suspendedUsers: number;
  usersByRole: Record<RoleType, number>;
  recentActions: AdminAuditLog[];
}