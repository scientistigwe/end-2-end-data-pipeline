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
