// Base Response Types
export interface BaseResponse {
  message?: string;
  status: number;
}

export interface SettingsResponse extends BaseResponse {
  data: UserSettings;
}

export interface SettingsValidationResponse extends BaseResponse {
  data: {
    valid: boolean;
    errors?: Array<{
      field: string;
      message: string;
    }>;
  };
}

// Settings Types
export interface UserSettings {
  data: {
    valid: boolean;
    errors?: Array<{
      field: string;
      message: string;
    }>;
  };
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

export type UpdateSettingsDto = Partial<UserSettings>;

// Event Types
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

export interface SettingsSyncedDetail {
  userId: string;
  settings: UserSettings;
  source: 'local' | 'remote';
  timestamp: string;
}

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

export type SettingsEventMap = {
  'settings:updated': CustomEvent<SettingsUpdatedDetail>;
  'settings:synced': CustomEvent<SettingsSyncedDetail>;
  'settings:error': CustomEvent<SettingsErrorDetail>;
};

export type SettingsEventName = keyof SettingsEventMap;