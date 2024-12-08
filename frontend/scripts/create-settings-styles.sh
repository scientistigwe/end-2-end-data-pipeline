#!/bin/bash

# Create settings module structure
mkdir -p src/settings/{api,components,hooks,store,types}

# Create settings API files
cat > src/settings/api/client.ts << 'EOL'
import { axiosClient } from '@/common/api/client/axiosClient';

class SettingsApiClient extends axiosClient {
  constructor() {
    super();
  }
}

export const settingsClient = new SettingsApiClient();
EOL

cat > src/settings/api/config.ts << 'EOL'
export const SETTINGS_CONFIG = {
  ENDPOINTS: {
    PROFILE: '/settings/profile',
    PREFERENCES: '/settings/preferences',
    SECURITY: '/settings/security',
    NOTIFICATIONS: '/settings/notifications',
    APPEARANCE: '/settings/appearance'
  }
} as const;
EOL

cat > src/settings/api/settingsApi.ts << 'EOL'
import { settingsClient } from './client';
import { SETTINGS_CONFIG } from './config';
import type { ApiResponse } from '@/common/types/api';
import type { UserSettings, UpdateSettingsDto } from '../types/settings';

class SettingsApi {
  async getUserSettings(): Promise<ApiResponse<UserSettings>> {
    return settingsClient.request('get', SETTINGS_CONFIG.ENDPOINTS.PROFILE);
  }

  async updateSettings(settings: UpdateSettingsDto): Promise<ApiResponse<UserSettings>> {
    return settingsClient.request('put', SETTINGS_CONFIG.ENDPOINTS.PROFILE, {}, settings);
  }
}

export const settingsApi = new SettingsApi();
EOL

cat > src/settings/api/index.ts << 'EOL'
export * from './settingsApi';
export * from './config';
EOL

# Create settings components
cat > src/settings/components/ProfileSettings.tsx << 'EOL'
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
EOL

cat > src/settings/components/SecuritySettings.tsx << 'EOL'
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
EOL

cat > src/settings/components/index.ts << 'EOL'
export * from './ProfileSettings';
export * from './SecuritySettings';
EOL

# Create settings hooks
cat > src/settings/hooks/useSettings.ts << 'EOL'
import { useQuery, useMutation } from 'react-query';
import { useDispatch } from 'react-redux';
import { settingsApi } from '../api';
import { setSettings } from '../store/settingsSlice';
import type { UpdateSettingsDto } from '../types/settings';

export const useSettings = () => {
  const dispatch = useDispatch();

  const { data: settings, isLoading } = useQuery(
    'settings',
    settingsApi.getUserSettings
  );

  const { mutate: updateSettings } = useMutation(
    (data: UpdateSettingsDto) => settingsApi.updateSettings(data),
    {
      onSuccess: (response) => {
        dispatch(setSettings(response.data));
      }
    }
  );

  return {
    settings: settings?.data,
    isLoading,
    updateSettings
  };
};
EOL

cat > src/settings/hooks/index.ts << 'EOL'
export * from './useSettings';
EOL

# Create settings store
cat > src/settings/store/settingsSlice.ts << 'EOL'
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { UserSettings } from '../types/settings';

interface SettingsState {
  settings: UserSettings | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: SettingsState = {
  settings: null,
  isLoading: false,
  error: null
};

const settingsSlice = createSlice({
  name: 'settings',
  initialState,
  reducers: {
    setSettings: (state, action: PayloadAction<UserSettings>) => {
      state.settings = action.payload;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    }
  }
});

export const { setSettings, setLoading, setError } = settingsSlice.actions;
export default settingsSlice.reducer;
EOL

cat > src/settings/store/selectors.ts << 'EOL'
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '@/store/store';

export const selectSettings = (state: RootState) => state.settings.settings;
export const selectSettingsLoading = (state: RootState) => state.settings.isLoading;
export const selectSettingsError = (state: RootState) => state.settings.error;
EOL

cat > src/settings/store/index.ts << 'EOL'
export * from './settingsSlice';
export * from './selectors';
EOL

# Create settings types
cat > src/settings/types/settings.ts << 'EOL'
export interface UserSettings {
  theme: 'light' | 'dark' | 'system';
  language: string;
  notifications: {
    email: boolean;
    push: boolean;
    desktop: boolean;
  };
  security: {
    twoFactorEnabled: boolean;
    lastPasswordChange: string;
  };
  preferences: Record<string, unknown>;
}

export interface UpdateSettingsDto {
  theme?: UserSettings['theme'];
  language?: string;
  notifications?: Partial<UserSettings['notifications']>;
  security?: Partial<UserSettings['security']>;
  preferences?: Record<string, unknown>;
}
EOL

cat > src/settings/types/index.ts << 'EOL'
export * from './settings';
EOL

# Create settings index
cat > src/settings/index.ts << 'EOL'
export * from './api';
export * from './components';
export * from './hooks';
export * from './store';
export * from './types';
EOL

# Create styles structure
mkdir -p src/styles/{global,theme,variables}

# Create global styles
cat > src/styles/global/reset.css << 'EOL'
/* Reset CSS */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-size: 16px;
  -webkit-text-size-adjust: 100%;
}

body {
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

img,
picture,
video,
canvas,
svg {
  display: block;
  max-width: 100%;
}

input,
button,
textarea,
select {
  font: inherit;
}

p,
h1,
h2,
h3,
h4,
h5,
h6 {
  overflow-wrap: break-word;
}
EOL

cat > src/styles/global/base.css << 'EOL'
/* Base styles */
:root {
  --font-sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

body {
  font-family: var(--font-sans);
  background-color: var(--background);
  color: var(--text-primary);
}

/* Add more base styles as needed */
EOL

# Create theme files
cat > src/styles/theme/colors.ts << 'EOL'
export const colors = {
  primary: {
    50: '#f0f9ff',
    100: '#e0f2fe',
    500: '#0ea5e9',
    600: '#0284c7',
    700: '#0369a1',
  },
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
  },
  // Add more colors as needed
} as const;
EOL

cat > src/styles/theme/typography.ts << 'EOL'
export const typography = {
  fonts: {
    sans: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif',
    mono: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
  },
  sizes: {
    xs: '0.75rem',
    sm: '0.875rem',
    base: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    '2xl': '1.5rem',
  },
  weights: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
} as const;
EOL

cat > src/styles/theme/spacing.ts << 'EOL'
export const spacing = {
  px: '1px',
  0: '0',
  0.5: '0.125rem',
  1: '0.25rem',
  2: '0.5rem',
  3: '0.75rem',
  4: '1rem',
  5: '1.25rem',
  6: '1.5rem',
  8: '2rem',
  10: '2.5rem',
  12: '3rem',
  16: '4rem',
  20: '5rem',
  24: '6rem',
  32: '8rem',
  40: '10rem',
  48: '12rem',
  56: '14rem',
  64: '16rem',
} as const;
EOL

# Create CSS variables
cat > src/styles/variables/colors.css << 'EOL'
:root {
  --background: #ffffff;
  --text-primary: #111827;
  --text-secondary: #4b5563;
  
  --primary-50: #f0f9ff;
  --primary-100: #e0f2fe;
  --primary-500: #0ea5e9;
  --primary-600: #0284c7;
  --primary-700: #0369a1;
  
  /* Add more color variables */
}

[data-theme="dark"] {
  --background: #111827;
  --text-primary: #f9fafb;
  --text-secondary: #d1d5db;
  
  /* Add dark theme overrides */
}
EOL

cat > src/styles/variables/layout.css << 'EOL'
:root {
  --header-height: 4rem;
  --sidebar-width: 16rem;
  --content-max-width: 1280px;
  
  --spacing-page: 1.5rem;
  --spacing-card: 1rem;
  --spacing-input: 0.5rem;
  
  --border-radius-sm: 0.25rem;
  --border-radius-md: 0.375rem;
  --border-radius-lg: 0.5rem;
  
  /* Add more layout variables */
}
EOL

echo "Settings module and styles structure created successfully!"