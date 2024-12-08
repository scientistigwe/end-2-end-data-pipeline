// src/decisions/api/client.ts
import { AxiosClient } from '../../common/api/client/axiosClient';
import { API_CONFIG } from './config';
import type { AxiosRequestConfig } from 'axios';
import type { ApiRequestConfig } from '../../common/types/api';

export class DecisionsApiClient extends AxiosClient {
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
    config?: Omit<ApiRequestConfig, 'method'>,
    data?: unknown
  ) {
    return super.request<T>(method, url, config, data);
  }
}

export const decisionsClient = new DecisionsApiClient();
