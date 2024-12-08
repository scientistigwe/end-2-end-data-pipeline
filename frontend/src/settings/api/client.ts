import { axiosClient } from '@/common/api/client/axiosClient';

class SettingsApiClient extends axiosClient {
  constructor() {
    super();
  }
}

export const settingsClient = new SettingsApiClient();
