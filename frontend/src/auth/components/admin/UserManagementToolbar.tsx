// src/auth/components/admin/UserManagementToolbar.tsx
import React from 'react';
import { Search, Filter, UserPlus, Trash2, Shield } from 'lucide-react';
import { Button } from '@/common/components/ui/button';
import { Input } from '@/common/components/ui/inputs/input';
import { Select } from '@/common/components/ui/select';
import { USER_ROLES } from '../../constants';
import { usePermissions } from '../../hooks/usePermissions';

interface UserManagementToolbarProps {
  selectedUsers: string[];
  onSearch: (query: string) => void;
  onFilter: (filters: UserFilters) => void;
  onCreateUser: () => void;
  onBulkAction: (action: BulkAction) => void;
}

export const UserManagementToolbar: React.FC<UserManagementToolbarProps> = ({
  selectedUsers,
  onSearch,
  onFilter,
  onCreateUser,
  onBulkAction
}) => {
  const { hasAllPermissions } = usePermissions();
  const canManageUsers = hasAllPermissions(['manage:users', 'delete:users']);
  const canUpdateRoles = hasAllPermissions(['manage:users', 'manage:roles']);

  return (
    <div className="flex flex-col space-y-4 md:flex-row md:space-y-0 md:space-x-4 md:items-center">
      <div className="flex-1 flex space-x-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search users..."
            className="pl-9"
            onChange={(e) => onSearch(e.target.value)}
          />
        </div>
        
        <Select
          className="w-40"
          onChange={(e) => onFilter({ role: e.target.value })}
        >
          <option value="">All Roles</option>
          {Object.entries(USER_ROLES).map(([key, value]) => (
            <option key={value} value={value}>
              {key.charAt(0) + key.slice(1).toLowerCase()}
            </option>
          ))}
        </Select>
      </div>

      <div className="flex space-x-2">
        {selectedUsers.length > 0 && (
          <>
            {canManageUsers && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => onBulkAction({ type: 'delete', payload: selectedUsers })}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Selected
              </Button>
            )}
            
            {canUpdateRoles && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onBulkAction({ 
                  type: 'updateRole', 
                  payload: { users: selectedUsers }
                })}
              >
                <Shield className="h-4 w-4 mr-2" />
                Update Roles
              </Button>
            )}
          </>
        )}

        {canManageUsers && (
          <Button onClick={onCreateUser}>
            <UserPlus className="h-4 w-4 mr-2" />
            Add User
          </Button>
        )}
      </div>
    </div>
  );
};

