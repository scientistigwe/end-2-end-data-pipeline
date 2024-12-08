  // src/auth/components/admin/EnhancedUserManagement.tsx
  import React, { useState } from 'react';
  import { usePermissions } from '../../hooks/usePermissions';
  import { UserManagementToolbar } from './UserManagementToolbar';
  import { UserManagementDialog } from './UserManagementDialog';
  import { BulkActionDialog } from './BulkActionDialog';
  import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/common/components/ui/table';
  import { Checkbox } from '@/common/components/ui/checkbox';
  import type { User } from '../../types/auth';
  import type { BulkAction, UserFilters } from '../../types/admin';
  
  export const EnhancedUserManagement: React.FC = () => {
    const [selectedUsers, setSelectedUsers] = useState<string[]>([]);
    const [filters, setFilters] = useState<UserFilters>({});
    const [dialogState, setDialogState] = useState<{
      type: 'create' | 'edit' | 'bulk' | null;
      data?: any;
    }>({ type: null });
  
    const { hasPermission } = usePermissions();
  
    const handleUserSelection = (userId: string, selected: boolean) => {
      setSelectedUsers(prev =>
        selected 
          ? [...prev, userId]
          : prev.filter(id => id !== userId)
      );
    };
  
    const handleBulkAction = async (action: BulkAction) => {
      try {
        switch (action.type) {
          case 'delete':
            // Implement bulk delete
            break;
          case 'updateRole':
            setDialogState({ type: 'bulk', data: { action, users: selectedUsers } });
            break;
          default:
            console.warn('Unhandled bulk action:', action);
        }
      } catch (error) {
        console.error('Bulk action failed:', error);
      }
    };
  
    const handleFilter = (newFilters: Partial<UserFilters>) => {
      setFilters(prev => ({ ...prev, ...newFilters }));
    };
  
    const canManageUser = (user: User) => {
      // Prevent managing users with higher roles
      if (user.role === 'admin' && !hasPermission('manage:admins')) {
        return false;
      }
      return hasPermission('manage:users');
    };
  
    return (
      <div className="space-y-4">
        <UserManagementToolbar
          selectedUsers={selectedUsers}
          onSearch={(query) => handleFilter({ searchQuery: query })}
          onFilter={handleFilter}
          onCreateUser={() => setDialogState({ type: 'create' })}
          onBulkAction={handleBulkAction}
        />
  
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <Checkbox
                  checked={selectedUsers.length > 0}
                  onClick={() => setSelectedUsers([])}
                />
              </TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Last Login</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {/* Table rows implementation */}
          </TableBody>
        </Table>
  
        {dialogState.type === 'create' && (
          <UserManagementDialog
            open={true}
            onClose={() => setDialogState({ type: null })}
            onSubmit={async (data) => {
              // Implement create
              setDialogState({ type: null });
            }}
          />
        )}
  
        {dialogState.type === 'bulk' && (
          <BulkActionDialog
            open={true}
            action={dialogState.data.action}
            users={dialogState.data.users}
            onClose={() => setDialogState({ type: null })}
            onConfirm={async (data) => {
              // Implement bulk action
              setDialogState({ type: null });
            }}
          />
        )}
      </div>
    );
  };