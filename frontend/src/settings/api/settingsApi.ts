// src/settings/api/settingsApi.ts
import { BaseClient } from '@/common/api/client/baseClient';
import { API_CONFIG } from '@/common/api/client/config';
import type { ApiResponse } from '@/common/types/api';
import type { UserSettings, UpdateSettingsDto } from '../types/settings';

class SettingsApi extends BaseClient {
  private readonly SETTINGS_EVENTS = {
    UPDATED: 'settings:updated',
    SYNCED: 'settings:synced',
    ERROR: 'settings:error'
  };

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

  private handleSettingsError(error: any): Error {
    if (error.response?.status === 409) {
      return new Error('Settings update conflict. Please refresh and try again.');
    }
    if (error.response?.status === 400) {
      return new Error(`Invalid settings: ${error.response.data?.message}`);
    }
    return error;
  }

  private handleSettingsEvents(response: any) {
    const url = response.config.url;
    if (response.config.method === 'put' && url?.includes('/settings')) {
      this.dispatchEvent(this.SETTINGS_EVENTS.UPDATED, response.data);
    }
  }

  private notifyError(error: Error): void {
    this.dispatchEvent(this.SETTINGS_EVENTS.ERROR, { error: error.message });
  }

  private dispatchEvent(eventName: string, detail: unknown): void {
    window.dispatchEvent(new CustomEvent(eventName, { detail }));
  }

  // Core Settings Operations
  async getUserSettings(): Promise<ApiResponse<UserSettings>> {
    const response = await this.get(API_CONFIG.ENDPOINTS.SETTINGS.PROFILE);
    this.dispatchEvent(this.SETTINGS_EVENTS.SYNCED, response.data);
    return response;
  }

  async updateSettings(settings: UpdateSettingsDto): Promise<ApiResponse<UserSettings>> {
    return this.put(
      API_CONFIG.ENDPOINTS.SETTINGS.PROFILE,
      settings
    );
  }

  // Helper Methods
  async validateSettings(settings: UpdateSettingsDto): Promise<boolean> {
    try {
      await this.post(
        API_CONFIG.ENDPOINTS.SETTINGS.VALIDATE,
        settings
      );
      return true;
    } catch (error) {
      return false;
    }
  }

  async syncSettings(): Promise<void> {
    const localSettings = localStorage.getItem('userSettings');
    if (localSettings) {
      try {
        const parsedSettings = JSON.parse(localSettings);
        await this.updateSettings(parsedSettings);
      } catch (error) {
        console.error('Failed to sync local settings:', error);
      }
    }
  }

  async resetSettings(): Promise<ApiResponse<UserSettings>> {
    return this.post(API_CONFIG.ENDPOINTS.SETTINGS.RESET);
  }

  // Settings Cache Management
  cacheSettings(settings: UserSettings): void {
    localStorage.setItem('userSettings', JSON.stringify(settings));
  }

  getCachedSettings(): UserSettings | null {
    const cached = localStorage.getItem('userSettings');
    return cached ? JSON.parse(cached) : null;
  }

  clearCachedSettings(): void {
    localStorage.removeItem('userSettings');
  }

  // Event Subscription
  subscribeToEvents(
    event: keyof typeof this.SETTINGS_EVENTS,
    callback: (event: CustomEvent) => void
  ): () => void {
    const handler = (e: Event) => callback(e as CustomEvent);
    window.addEventListener(this.SETTINGS_EVENTS[event], handler);
    return () => window.removeEventListener(this.SETTINGS_EVENTS[event], handler);
  }
}

// Export singleton instance
export const settingsApi = new SettingsApi();