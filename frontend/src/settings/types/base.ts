// src/settings/types/base.ts
export interface BaseResponse {
    message?: string;
    status: number;
  }
  
  export const SETTINGS_EVENTS = {
    UPDATED: 'settings:updated',
    SYNCED: 'settings:synced',
    ERROR: 'settings:error'
  } as const;
  
  export interface AppearanceSettings {
    theme: 'light' | 'dark' | 'system';
    fontSize: number;
    density: 'comfortable' | 'compact';
    animations: boolean;
  }
  
  export interface NotificationSettings {
    desktop: boolean;
    email: boolean;
    push: boolean;
    frequency: 'instant' | 'daily' | 'weekly';
    types: string[];
  }
  
  export interface PrivacySettings {
    shareData: boolean;
    analytics: boolean;
  }
  
  export interface PreferenceSettings {
    language: string;
    timezone: string;
    dateFormat: string;
    startPage: string;
  }
  
  export interface SecuritySettings {
    twoFactorEnabled: boolean;
    lastPasswordChange: string;
  }