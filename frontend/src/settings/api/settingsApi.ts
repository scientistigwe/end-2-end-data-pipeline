// src/settings/api/settingsApi.ts

import { BaseClient } from '@/common/api/client/baseClient';
import { API_CONFIG } from '@/common/api/client/config';
import type { ApiResponse } from '@/common/types/api';
import type {
  UserSettings,
  UpdateSettingsDto,
  SettingsError,
  SettingsEventMap,
  SettingsEventName,
  SettingsUpdatedDetail,
  SettingsSyncedDetail,
  SettingsErrorDetail
} from '../types/settings';
import { SETTINGS_EVENTS } from '../types/settings';

class SettingsApi extends BaseClient {
  private readonly SETTINGS_EVENTS = SETTINGS_EVENTS;
  private readonly CACHE_KEY = 'userSettings';

  constructor() {
    super({
      baseURL: import.meta.env.VITE_SETTINGS_API_URL || API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        ...API_CONFIG.DEFAULT_HEADERS,
        'X-Service': 'settings'
      }
    });

    this.setupSettingsInterceptors();
  }

  // Interceptors and Error Handling
  private setupSettingsInterceptors() {
    this.client.interceptors.request.use(
      (config) => {
        config.headers.set('X-Settings-Timestamp', new Date().toISOString());
        return config;
      }
    );

    this.client.interceptors.response.use(
      response => {
        this.handleSettingsEvents(response);
        return response;
      },
      error => {
        const enhancedError = this.handleSettingsError(error);
        this.notifyError(enhancedError);
        throw enhancedError;
      }
    );
  }

  private handleSettingsError(error: unknown): SettingsError {
    const baseError: SettingsError = {
      name: 'SettingsError',
      message: 'Unknown settings error',
      timestamp: new Date().toISOString(),
      component: 'settings',
      details: {}
    };

    if (error instanceof Error) {
      return {
        ...error,
        ...baseError,
        message: error.message
      };
    }

    if (typeof error === 'object' && error !== null) {
      const errorObj = error as Record<string, any>;
      if (errorObj.config?.headers?.['X-User-ID']) {
        baseError.details.userId = errorObj.config.headers['X-User-ID'];
      }

      if (errorObj.response?.status === 409) {
        return {
          ...baseError,
          message: 'Settings update conflict. Please refresh and try again.',
          code: 'SETTINGS_CONFLICT'
        };
      }

      if (errorObj.response?.status === 400) {
        return {
          ...baseError,
          message: `Invalid settings: ${errorObj.response.data?.message}`,
          code: 'INVALID_SETTINGS'
        };
      }
    }

    return baseError;
  }

  // Event Management
  private handleSettingsEvents(response: any): void {
    const url = response.config.url;
    const userId = response.config.headers?.['X-User-ID'];

    if (response.config.method === 'put' && url?.includes('/settings')) {
      const settings = response.data as UserSettings;
      this.notifyUpdated(userId, settings);
    }
  }

  private notifyError(error: SettingsError): void {
    window.dispatchEvent(
      new CustomEvent<SettingsErrorDetail>(this.SETTINGS_EVENTS.ERROR, {
        detail: {
          error: error.message,
          code: error.code,
          userId: error.details.userId || 'unknown'
        }
      })
    );
  }

  private notifyUpdated(userId: string, settings: UserSettings): void {
    window.dispatchEvent(
      new CustomEvent<SettingsUpdatedDetail>(this.SETTINGS_EVENTS.UPDATED, {
        detail: {
          userId,
          settings,
          timestamp: new Date().toISOString()
        }
      })
    );
  }

  private notifySynced(userId: string, settings: UserSettings, source: 'local' | 'remote'): void {
    window.dispatchEvent(
      new CustomEvent<SettingsSyncedDetail>(this.SETTINGS_EVENTS.SYNCED, {
        detail: { userId, settings, source }
      })
    );
  }

  // Core Settings Operations
  async getUserSettings(): Promise<ApiResponse<UserSettings>> {
    const response = await this.get<UserSettings>(
      this.getRoute('SETTINGS', 'PROFILE')
    );
    this.notifySynced('current', response.data, 'remote');
    return response;
  }

  async updateSettings(settings: UpdateSettingsDto): Promise<ApiResponse<UserSettings>> {
    const response = await this.put<UserSettings>(
      this.getRoute('SETTINGS', 'PROFILE'),
      settings
    );
    return response;
  }

  async validateSettings(settings: UpdateSettingsDto): Promise<boolean> {
    try {
      await this.post<{ valid: boolean }>(
        this.getRoute('SETTINGS', 'VALIDATE'),
        settings
      );
      return true;
    } catch (error) {
      return false;
    }
  }

  async resetSettings(): Promise<ApiResponse<UserSettings>> {
    const response = await this.post<UserSettings>(
      this.getRoute('SETTINGS', 'RESET')
    );
    return response;
  }

  // Cache Management
  async syncSettings(): Promise<void> {
    const localSettings = this.getCachedSettings();
    if (localSettings) {
      try {
        const response = await this.updateSettings(localSettings);
        this.notifySynced('current', response.data, 'local');
      } catch (error) {
        console.error('Failed to sync local settings:', error);
        throw this.handleSettingsError(error);
      }
    }
  }

  cacheSettings(settings: UserSettings): void {
    localStorage.setItem(this.CACHE_KEY, JSON.stringify(settings));
  }

  getCachedSettings(): UserSettings | null {
    const cached = localStorage.getItem(this.CACHE_KEY);
    return cached ? JSON.parse(cached) : null;
  }

  clearCachedSettings(): void {
    localStorage.removeItem(this.CACHE_KEY);
  }

  // Event Subscription
  subscribeToEvents<E extends SettingsEventName>(
    event: E,
    callback: (event: SettingsEventMap[E]) => void
  ): () => void {
    const handler = (e: Event) => callback(e as SettingsEventMap[E]);
    window.addEventListener(event, handler);
    return () => window.removeEventListener(event, handler);
  }
}

export const settingsApi = new SettingsApi();