// src/common/types/api.ts
import type { AxiosRequestConfig } from 'axios';

// Base API Types
export interface ApiRequestConfig extends Omit<AxiosRequestConfig, 'onUploadProgress'> {
  routeParams?: Record<string, string>;
  onUploadProgress?: (progress: number) => void;
}

export interface ApiResponse<T = unknown> {
  data: T;
  message?: string;
  status: number;
}

// Error Types
export interface ApiError {
  code: string;
  message: string;
  status?: number;
  details?: unknown;
}

export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    status: number;
    details?: Record<string, unknown>;
    timestamp?: string;
    path?: string;
    requestId?: string;
    validationErrors?: ValidationError[];
  };
  message?: string;
}

export type ApiErrorResponse = ErrorResponse | {
  message: string;
  [key: string]: unknown;
};

// Pagination Types
export interface PaginationParams {
  page: number;
  limit: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

export interface PaginationInfo {
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

export interface PaginatedResponse<T> extends ApiResponse<T> {
  pagination: PaginationInfo;
}

// Utility Types
export type ApiErrorFormatter = (error: unknown) => ApiError;

// HTTP Method Types
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

// Common Response Types
export interface SuccessResponse extends ApiResponse<null> {
  success: true;
}

export interface BulkOperationResponse extends ApiResponse<{
  succeeded: number;
  failed: number;
  errors?: ApiError[];
}> {}