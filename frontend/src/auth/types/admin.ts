// src/auth/types/admin.ts
export interface BulkAction {
    type: 'delete' | 'updateRole' | 'updatePermissions';
    payload: any;
  }
  
  export interface UserFilters {
    role?: string;
    searchQuery?: string;
    status?: 'active' | 'inactive';
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
  }
  
  