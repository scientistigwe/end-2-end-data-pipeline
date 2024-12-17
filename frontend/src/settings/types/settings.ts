// src/settings/types/settings.ts

export interface SettingsResponse {
  data: UserSettings;
  message?: string;
  status: number;
}

export interface SettingsValidationResponse {
  valid: boolean;
  errors?: Array<{
    field: string;
    message: string;
  }>;
}

// Add to Event Detail types
export interface SettingsSyncedDetail {
  userId: string;
  settings: UserSettings; // Now explicitly typed
  source: 'local' | 'remote';
  timestamp?: string;
}

export interface UserSettings {
  appearance: {
    theme: 'light' | 'dark' | 'system';
    fontSize: number;
    density: 'comfortable' | 'compact';
    animations: boolean;
  };
  notifications: {
    desktop: boolean;
    email: boolean;
    push: boolean;
    frequency: 'instant' | 'daily' | 'weekly';
    types: string[];
  };
  privacy: {
    shareData: boolean;
    analytics: boolean;
  };
  preferences: {
    language: string;
    timezone: string;
    dateFormat: string;
    startPage: string;
  };
  security: {
    twoFactorEnabled: boolean;
    lastPasswordChange: string;
  };
}

export const SETTINGS_EVENTS = {
  UPDATED: 'settings:updated',
  SYNCED: 'settings:synced',
  ERROR: 'settings:error'
} as const;

export interface SettingsError extends Error {
  name: 'SettingsError';
  code?: string;
  timestamp: string;
  component: 'settings';
  details: {
    userId?: string;
    [key: string]: unknown;
  };
}



// Event Detail Types
export interface SettingsUpdatedDetail {
  userId: string;
  settings: UserSettings;
  timestamp: string;
}

export interface SettingsErrorDetail {
  error: string;
  code?: string;
  userId: string;
}


export type UpdateSettingsDto = Partial<UserSettings>;

// Event Map Type
export type SettingsEventMap = {
  'settings:updated': CustomEvent<SettingsUpdatedDetail>;
  'settings:synced': CustomEvent<SettingsSyncedDetail>;
  'settings:error': CustomEvent<SettingsErrorDetail>;
};

export type SettingsEventName = keyof SettingsEventMap;