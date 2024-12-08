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
