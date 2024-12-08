  // src/auth/components/admin/RoleSelector.tsx
  import React from 'react';
  import { Select } from '@/common/components/ui/select';
  import { useRBAC } from '../../hooks/useRBAC';
  import { USER_ROLES } from '../../constants';
  
  interface RoleSelectorProps {
    value: string;
    onChange: (role: string) => void;
    disabled?: boolean;
  }
  
  export const RoleSelector: React.FC<RoleSelectorProps> = ({
    value,
    onChange,
    disabled
  }) => {
    const { canAssignRole } = useRBAC();
  
    return (
      <Select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        {Object.entries(USER_ROLES).map(([key, roleValue]) => (
          canAssignRole(roleValue) && (
            <option key={roleValue} value={roleValue}>
              {key.charAt(0) + key.slice(1).toLowerCase()}
            </option>
          )
        ))}
      </Select>
    );
  };