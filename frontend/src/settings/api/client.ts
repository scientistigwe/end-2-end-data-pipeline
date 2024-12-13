import { BaseClient } from '@/common/api/client/baseClient';

class SettingsApiClient extends BaseClient {
  constructor() {
    super();
  }
}

export const settingsClient = new SettingsApiClient();
