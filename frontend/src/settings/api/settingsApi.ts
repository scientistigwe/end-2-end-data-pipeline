import { baseAxiosClient } from '@/common/api/client/baseClient';
import type { 
  UserSettings,
  UpdateSettingsDto,
  SettingsError,
  SettingsEventMap,
  SettingsEventName,
  SettingsUpdatedDetail,
  SettingsSyncedDetail,
  SettingsErrorDetail,
  SettingsResponse,
  SettingsValidationResponse
} from '../types/settings';
import { SETTINGS_EVENTS } from '../types/settings';
import type { AxiosResponse } from 'axios';

class SettingsApi {
  private client = baseAxiosClient;
  private readonly SETTINGS_EVENTS = SETTINGS_EVENTS;
  private readonly CACHE_KEY = 'userSettings';

  constructor() {
    this.setupSettingsHeaders();
    this.setupSettingsInterceptors();
  }

  private setupSettingsHeaders() {
    this.client.setDefaultHeaders({
      'X-Service': 'settings'
    });
  }

  // Interceptors and Error Handling
  private setupSettingsInterceptors() {
    const instance = (this.client as any).client;
    if (!instance) return;

    instance.interceptors.request.use(
      (config: Record<string, any>) => {
        if (config.headers) {
        }
        return config;
      }
    );

    instance.interceptors.response.use(
      (response: AxiosResponse) => {
        this.handleSettingsEvents(response);
        return response;
      },
      (error: unknown) => {
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
        ...baseError,
        ...error,
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
  private handleSettingsEvents(response: AxiosResponse): void {
    const url = response.config.url;
    const userId = response.config.headers?.['X-User-ID'] as string;

    if (response.config.method === 'put' && url?.includes('/settings')) {
      const settingsResponse = response.data as SettingsResponse;
      this.notifyUpdated(userId, settingsResponse.data);
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
        detail: {
          userId,
          settings,
          source,
          timestamp: new Date().toISOString()
        }
      })
    );
  }

  // Core Settings Operations
  async getUserSettings(): Promise<UserSettings> {
    const response = await this.client.executeGet<SettingsResponse>(
      this.client.createRoute('SETTINGS', 'PROFILE')
    );
    this.notifySynced('current', response.data.data, 'remote');
    return response.data.data;
  }

  async updateSettings(settings: UpdateSettingsDto): Promise<UserSettings> {
    const response = await this.client.executePut<SettingsResponse>(
      this.client.createRoute('SETTINGS', 'PROFILE'),
      settings
    );
    return response.data.data;
  }

  async validateSettings(settings: UpdateSettingsDto): Promise<boolean> {
    try {
      const response = await this.client.executePost<SettingsValidationResponse>(
        this.client.createRoute('SETTINGS', 'VALIDATE'),
        settings
      );
      return response.data.data.valid;
    } catch (error) {
      return false;
    }
  }

  async resetSettings(): Promise<UserSettings> {
    const response = await this.client.executePost<SettingsResponse>(
      this.client.createRoute('SETTINGS', 'RESET')
    );
    return response.data.data;
  }

  // Cache Management
  async syncSettings(): Promise<void> {
    const localSettings = this.getCachedSettings();
    if (localSettings) {
      try {
        const settings = await this.updateSettings(localSettings);
        this.notifySynced('current', settings, 'local');
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

// Export singleton instance
export const settingsApi = new SettingsApi();