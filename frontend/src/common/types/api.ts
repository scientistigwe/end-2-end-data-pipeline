// src/common/types/api.ts
import type { AxiosRequestConfig } from 'axios';

export interface ApiRequestConfig extends Omit<AxiosRequestConfig, 'onUploadProgress'> {
  routeParams?: Record<string, string>;
  onUploadProgress?: (progress: number) => void;
}

export interface ApiError {
  code: string;
  message: string;
  status?: number;
  details?: unknown;
}

export interface ApiResponse<T = unknown> {
  data: T;
  message?: string;
  status: number;
}

export interface PaginationParams {
  page: number;
  limit: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> extends ApiResponse<T> {
  pagination: {
    total: number;
    page: number;
    limit: number;
    totalPages: number;
  };
}


