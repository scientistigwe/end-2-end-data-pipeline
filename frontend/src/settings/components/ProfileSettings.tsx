import React from 'react';
import { useSettings } from '../hooks/useSettings';

export const ProfileSettings: React.FC = () => {
  const { settings, updateSettings } = useSettings();

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-medium">Profile Settings</h2>
      {/* Profile settings form */}
    </div>
  );
};
