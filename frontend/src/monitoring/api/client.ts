// src/monitoring/api/client.ts
import { API_CONFIG } from './config';
import type { AxiosRequestConfig } from 'axios';
import { BaseClient } from '../../common/api/client/baseClient'; // Import the class, not the instance

export class MonitoringApiClient extends BaseClient {
  constructor() {
    const config: AxiosRequestConfig = {
      baseURL: API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json'
      }
    };
    super(config);
  }

  public override request<T>(
    method: 'get' | 'post' | 'put' | 'delete',
    url: string,
    config?: Omit<AxiosRequestConfig, 'method'>,
    data?: unknown
  ) {
    return super.request<T>(method, url, config, data);
  }
}

export const monitoringClient = new MonitoringApiClient();


