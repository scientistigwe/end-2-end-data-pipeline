import { axiosClient } from '@/common/api/client/baseClient';

class SettingsApiClient extends axiosClient {
  constructor() {
    super();
  }
}

export const settingsClient = new SettingsApiClient();
