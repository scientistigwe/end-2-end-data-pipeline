// src/common/api/config.ts
import type { AxiosRequestConfig, AxiosProgressEvent } from 'axios';

export const API_CONFIG = {
  BASE_URL: import.meta.env.REACT_APP_API_URL || '/api/v1',
  TIMEOUT: 30000,
  RETRY_COUNT: 3,
  DEFAULT_HEADERS: {
    'Content-Type': 'application/json'
  }
} as const;

// Helper Types
export type EndpointParams = Record<string, string>;

export interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
}

export interface ApiRequestConfig extends Omit<AxiosRequestConfig, 'url' | 'method' | 'data'> {
  routeParams?: EndpointParams;
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void;
}