// src/settings/api/settingsApi.ts
import { RouteHelper } from '@/common/api/routes';
import { baseAxiosClient } from '@/common/api/client/baseClient';
import { HTTP_STATUS } from '@/common/types/api';
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios';
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
  SettingsValidationResponse,
  ApiResponse
} from '../types';

import { SETTINGS_EVENTS } from '../types';


// src/settings/api/settingsApi.ts




interface SettingsErrorMetadata {
  retryable: boolean;
  critical: boolean;
  code: string;
}

class SettingsApi {
  private client = baseAxiosClient;
  private static readonly CACHE_KEY = 'userSettings';
  private static readonly ERROR_METADATA: Record<number, SettingsErrorMetadata> = {
    [HTTP_STATUS.CONFLICT]: {
      retryable: true,
      critical: false,
      code: 'SETTINGS_CONFLICT'
    },
    [HTTP_STATUS.BAD_REQUEST]: {
      retryable: false,
      critical: true,
      code: 'INVALID_SETTINGS'
    }
  };

  constructor() {
    this.setupSettingsHeaders();
    this.setupSettingsInterceptors();
  }

  private setupSettingsHeaders(): void {
    this.client.setDefaultHeaders({
      'X-Service': 'settings'
    });
  }

  private setupSettingsInterceptors(): void {
    const instance = this.client.getAxiosInstance();
    if (!instance) return;

    instance.interceptors.request.use(
      this.handleRequestInterceptor,
      this.handleRequestError
    );

    instance.interceptors.response.use(
      this.handleResponseInterceptor,
      this.handleResponseError
    );
  }

  private handleRequestInterceptor = (
    config: InternalAxiosRequestConfig
  ): InternalAxiosRequestConfig | Promise<InternalAxiosRequestConfig> => {
    return config;
  };

  private handleRequestError = (error: unknown): Promise<never> => {
    return Promise.reject(this.handleSettingsError(error));
  };

  private handleResponseInterceptor = (
    response: AxiosResponse
  ): AxiosResponse | Promise<AxiosResponse> => {
    this.handleSettingsEvents(response);
    return response;
  };

  private handleResponseError = (error: unknown): Promise<never> => {
    const enhancedError = this.handleSettingsError(error);
    this.notifyError(enhancedError);
    throw enhancedError;
  };

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
        message: error.message,
        stack: error.stack
      };
    }

    if (typeof error === 'object' && error !== null) {
      const errorObj = error as Record<string, any>;
      
      if (errorObj.config?.headers?.['X-User-ID']) {
        baseError.details.userId = errorObj.config.headers['X-User-ID'];
      }

      const status = errorObj.response?.status;
      const errorMetadata = SettingsApi.ERROR_METADATA[status];

      if (errorMetadata) {
        return {
          ...baseError,
          code: errorMetadata.code,
          message: this.getErrorMessage(errorMetadata.code, errorObj.response?.data)
        };
      }
    }

    return baseError;
  }

  private getErrorMessage(code: string, data?: any): string {
    switch (code) {
      case 'SETTINGS_CONFLICT':
        return 'Settings update conflict. Please refresh and try again.';
      case 'INVALID_SETTINGS':
        return `Invalid settings: ${data?.message || ''}`;
      default:
        return 'An error occurred while managing settings';
    }
  }

  // Event Notification Methods
  private notifyError(error: SettingsError): void {
    window.dispatchEvent(
      new CustomEvent<SettingsErrorDetail>(SETTINGS_EVENTS.ERROR, {
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
      new CustomEvent<SettingsUpdatedDetail>(SETTINGS_EVENTS.UPDATED, {
        detail: {
          userId,
          settings,
          timestamp: new Date().toISOString()
        }
      })
    );
  }

  private notifySynced(
    userId: string, 
    settings: UserSettings, 
    source: 'local' | 'remote'
  ): void {
    window.dispatchEvent(
      new CustomEvent<SettingsSyncedDetail>(SETTINGS_EVENTS.SYNCED, {
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
  private handleSettingsEvents(response: AxiosResponse): void {
    const url = response.config.url;
    const userId = response.config.headers?.['X-User-ID'] as string;

    if (response.config.method === 'put' && url?.includes('/settings')) {
      const settingsResponse = response.data as ApiResponse<UserSettings>;
      this.notifyUpdated(userId, settingsResponse.data);
    }
  }

  async getUserSettings(): Promise<UserSettings> {
    const response = await this.client.executeGet<SettingsResponse>(
      RouteHelper.getRoute('SETTINGS', 'PROFILE')
    );
    this.notifySynced('current', response.data.data, 'remote');
    return response.data.data;
  }

  async updateSettings(settings: UpdateSettingsDto): Promise<UserSettings> {
    const response = await this.client.executePut<SettingsResponse>(
      RouteHelper.getRoute('SETTINGS', 'PROFILE'),
      settings
    );
    return response.data.data;
  }

  async validateSettings(settings: UpdateSettingsDto): Promise<boolean> {
    try {
      const response = await this.client.executePost<SettingsValidationResponse>(
        RouteHelper.getRoute('SETTINGS', 'VALIDATE'),
        settings
      );
      return response.data.data.valid;
    } catch (error) {
      return false;
    }
  }

  async resetSettings(): Promise<UserSettings> {
    const response = await this.client.executePost<SettingsResponse>(
      RouteHelper.getRoute('SETTINGS', 'RESET')
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
        throw this.handleSettingsError(error);
      }
    }
  }

  cacheSettings(settings: UserSettings): void {
    localStorage.setItem(SettingsApi.CACHE_KEY, JSON.stringify(settings));
  }

  getCachedSettings(): UserSettings | null {
    const cached = localStorage.getItem(SettingsApi.CACHE_KEY);
    return cached ? JSON.parse(cached) : null;
  }

  clearCachedSettings(): void {
    localStorage.removeItem(SettingsApi.CACHE_KEY);
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