import { baseAxiosClient, ServiceType } from '@/common/api/client/baseClient';
import type { 
  UserSettings,
  UpdateSettingsDto,
  SettingsEventMap,
  SettingsEventName,
  SettingsUpdatedDetail,
  SettingsSyncedDetail,
  ValidationResult,
  SettingsResponse,
  SettingsValidationResponse,
  ServerResponse
} from '../types';



import { SETTINGS_EVENTS } from '../types';

class SettingsApi {
  private client = baseAxiosClient;
  private static readonly CACHE_KEY = 'userSettings';

  constructor() {
    this.client.setServiceConfig({
      service: ServiceType.SETTINGS,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      }
    });
  }

  // Core Settings Operations
  async getUserSettings(): Promise<UserSettings> {
    const response = await this.client.executeGet<SettingsResponse>(
      this.client.createRoute('SETTINGS', 'PROFILE')
    );
    
    const settings = response.data.data;
    this.notifySynced('current', settings, 'remote');
    return settings;
  }

  async updateSettings(settings: UpdateSettingsDto): Promise<UserSettings> {
    const response = await this.client.executePut<SettingsResponse>(
      this.client.createRoute('SETTINGS', 'PROFILE'), // Use PROFILE instead of UPDATE
      settings
    );
    
    const updatedSettings = response.data;
    this.notifyUpdated('current', updatedSettings);
    return updatedSettings;
  }

  async validateSettings(settings: UpdateSettingsDto): Promise<boolean> {
    try {
      const response = await this.client.executePost<ServerResponse<ValidationResult>>(
        this.client.createRoute('SETTINGS', 'VALIDATE'),
        settings
      );
      return response.data.valid;
    } catch (error) {
      return false;
    }
  }

  async resetSettings(): Promise<UserSettings> {
    const response = await this.client.executePost<ServerResponse<UserSettings>>(
      this.client.createRoute('SETTINGS', 'RESET')
    );
    return response.data;
  }

  // Cache Management
  async syncSettings(): Promise<void> {
    const localSettings = this.getCachedSettings();
    if (localSettings) {
      const settings = await this.updateSettings(localSettings);
      this.notifySynced('current', settings, 'local');
    }
  }

  cacheSettings(settings: UserSettings): void {
    try {
      localStorage.setItem(SettingsApi.CACHE_KEY, JSON.stringify(settings));
    } catch (error) {
      console.error('Failed to cache settings:', error);
    }
  }

  getCachedSettings(): UserSettings | null {
    try {
      const cached = localStorage.getItem(SettingsApi.CACHE_KEY);
      return cached ? JSON.parse(cached) : null;
    } catch (error) {
      console.error('Failed to retrieve cached settings:', error);
      return null;
    }
  }

  clearCachedSettings(): void {
    localStorage.removeItem(SettingsApi.CACHE_KEY);
  }

  // Event Notifications
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