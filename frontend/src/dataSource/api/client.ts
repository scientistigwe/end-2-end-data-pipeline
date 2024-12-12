import { AxiosClient } from '../../common/api/client/baseClient';
import { API_CONFIG } from './config';
import type { ApiRequestConfig, ApiResponse } from '@/common/types/api';
import type { AxiosProgressEvent, AxiosRequestConfig } from 'axios';

export class DataSourceApiClient extends AxiosClient {
  constructor() {
    super({
      baseURL: API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  public override request<T>(
    method: 'get' | 'post' | 'put' | 'delete',
    url: string,
    config?: Omit<ApiRequestConfig, 'method'>,
    data?: unknown
  ): Promise<ApiResponse<T>> {
    if (!config) {
      return super.request(method, url, undefined, data);
    }

    const { onUploadProgress, ...restConfig } = config;
    
    const transformedConfig: Omit<AxiosRequestConfig, 'method'> = {
      ...restConfig,
      onUploadProgress: onUploadProgress
        ? (e: AxiosProgressEvent) => {
            const progress = (e.loaded / (e.total ?? 1)) * 100;
            onUploadProgress(progress);
          }
        : undefined
    };

    return super.request(method, url, transformedConfig as ApiRequestConfig, data);
  }
}

export const dataSourceClient = new DataSourceApiClient();