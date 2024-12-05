// src/types/api.ts
import { AxiosError, AxiosRequestConfig, AxiosProgressEvent } from 'axios';

export interface ApiRequestConfig extends Omit<AxiosRequestConfig, 'onUploadProgress'> {
  routeParams?: Record<string, string>;
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void;
}

export interface ApiError {
  code: string;
  message: string;
  details?: unknown;
  status?: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
  message?: string;
  status: number;
}

export interface ErrorResponse {
  error: ApiError;
  status: number;
}

export type ApiErrorHandler = (error: AxiosError | ApiError) => void;
export type ApiErrorFormatter = (error: unknown) => ApiError;
export type ApiResponseFormatter = <T>(data: T) => ApiResponse<T>;

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





