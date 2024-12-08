import React from 'react';
import { useSettings } from '../hooks/useSettings';

export const SecuritySettings: React.FC = () => {
  const { settings, updateSecuritySettings } = useSettings();

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-medium">Security Settings</h2>
      {/* Security settings form */}
    </div>
  );
};
