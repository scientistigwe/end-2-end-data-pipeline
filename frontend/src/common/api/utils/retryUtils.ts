// src/common/api/utils/retryUtils.ts
import type { AxiosError } from 'axios';

interface RetryConfig {
  maxRetries?: number;
  retryDelay?: number;
  shouldRetry?: (error: AxiosError) => boolean;
}

export const createRetryConfig = (config?: RetryConfig) => {
  const defaultConfig: Required<RetryConfig> = {
    maxRetries: 3,
    retryDelay: 1000,
    shouldRetry: (error: AxiosError) => {
      return error.response?.status ? error.response.status >= 500 : false;
    },
    ...config
  };

  return defaultConfig;
};
