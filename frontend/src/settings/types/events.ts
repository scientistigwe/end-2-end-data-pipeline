// src/settings/types/events.ts
import type { UserSettings } from './models';
import { SETTINGS_EVENTS } from './base';

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
  [SETTINGS_EVENTS.UPDATED]: CustomEvent<SettingsUpdatedDetail>;
  [SETTINGS_EVENTS.SYNCED]: CustomEvent<SettingsSyncedDetail>;
  [SETTINGS_EVENTS.ERROR]: CustomEvent<SettingsErrorDetail>;
};

export type SettingsEventName = keyof SettingsEventMap;