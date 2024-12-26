// src/settings/types/models.ts
import type { 
  AppearanceSettings,
  NotificationSettings,
  PrivacySettings,
  PreferenceSettings,
  SecuritySettings
} from './base';

export interface UserSettings {
  appearance: AppearanceSettings;
  notifications: NotificationSettings;
  privacy: PrivacySettings;
  preferences: PreferenceSettings;
  security: SecuritySettings;
}

export interface ValidationError {
  field: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  errors?: ValidationError[];
}

export type UpdateSettingsDto = Partial<UserSettings>;