// src/auth/components/admin/UserManagementDialog.tsx
import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle
} from '@/common/components/ui/dialog';
import { UserForm } from './UserForm';
import type { User } from '../../types/auth';

interface UserManagementDialogProps {
  open: boolean;
  onClose: () => void;
  user?: Partial<User>;
  onSubmit: (data: Partial<User>) => Promise<void>;
}

export const UserManagementDialog: React.FC<UserManagementDialogProps> = ({
  open,
  onClose,
  user,
  onSubmit
}) => {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {user ? 'Edit User' : 'Create New User'}
          </DialogTitle>
        </DialogHeader>
        <UserForm
          user={user}
          onSubmit={onSubmit}
          onCancel={onClose}
        />
      </DialogContent>
    </Dialog>
  );
};