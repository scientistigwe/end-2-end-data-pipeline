// src/common/api/config.ts
import type { AxiosRequestConfig, AxiosProgressEvent, ResponseType } from 'axios';

// Environment configuration
const isDevelopment = import.meta.env.MODE === 'development';

// API Base Configuration
export const API_CONFIG = {
  // Base URL configuration
  BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:5000',
  VERSION: 'v1',
  TIMEOUT: 30000,
  RETRY_COUNT: 3,

  // Default headers
  DEFAULT_HEADERS: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Requested-With': 'XMLHttpRequest'
  },

  // CORS configuration
  CORS: {
    withCredentials: true,
    credentials: 'include' as const
  },

  // Upload configuration
  UPLOAD: {
    MAX_SIZE: 50 * 1024 * 1024, // 50MB
    SUPPORTED_FORMATS: [
      'image/jpeg',
      'image/png',
      'image/gif',
      'application/pdf',
      'text/csv',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // xlsx
      'application/vnd.ms-excel' // xls
    ],
    CHUNK_SIZE: 1024 * 1024 * 5 // 5MB chunks for large files
  }
} as const;

// Types
export interface ApiSuccessResponse<T> {
  data: T;
  message?: string;
  status: number;
  meta?: {
    page?: number;
    limit?: number;
    total?: number;
    totalPages?: number;
  };
}

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    details?: unknown;
    validationErrors?: Record<string, string[]>;
  };
  status: number;
}

export type ApiResponse<T> = ApiSuccessResponse<T>;

export interface ApiError {
  code: string;
  message: string;
  details?: unknown;
  status?: number;
  validationErrors?: Record<string, string[]>;
}

export interface ApiRequestConfig extends Omit<AxiosRequestConfig, 'url' | 'method' | 'data'> {
  routeParams?: Record<string, string>;
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void;
  onDownloadProgress?: (progressEvent: AxiosProgressEvent) => void;
  withCredentials?: boolean;
  responseType?: ResponseType;
  signal?: AbortSignal;
}

export interface PaginationParams {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  search?: string;
  filters?: Record<string, string | number | boolean | null>;
}

// Configuration Objects
export const DEFAULT_REQUEST_CONFIG: Partial<ApiRequestConfig> = {
  withCredentials: true,
  responseType: 'json',
  timeout: API_CONFIG.TIMEOUT
} as const;

export const RETRY_CONFIG = {
  count: API_CONFIG.RETRY_COUNT,
  delay: 1000,
  statuses: [408, 429, 500, 502, 503, 504],
  methods: ['get', 'head', 'options', 'put', 'delete'],
  backoffFactor: 2,
  maxDelay: 30000
} as const;

export const CACHE_CONFIG = {
  defaultDuration: 5 * 60 * 1000,
  maxSize: 100,
  cleanupInterval: 60 * 60 * 1000
} as const;

export const ENV_CONFIG = {
  isDevelopment,
  isProduction: import.meta.env.MODE === 'production',
  isTest: import.meta.env.MODE === 'test',
  apiUrl: API_CONFIG.BASE_URL,
  appUrl: import.meta.env.VITE_APP_URL || 'http://localhost:5173',
  debugMode: isDevelopment || import.meta.env.VITE_DEBUG === 'true'
} as const;

// Constants
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  ACCEPTED: 202,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  METHOD_NOT_ALLOWED: 405,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500,
  SERVICE_UNAVAILABLE: 503
} as const;

export const CONTENT_TYPES = {
  JSON: 'application/json',
  FORM_DATA: 'multipart/form-data',
  FORM_URLENCODED: 'application/x-www-form-urlencoded',
  TEXT: 'text/plain',
  HTML: 'text/html',
  XML: 'application/xml',
  BINARY: 'application/octet-stream'
} as const;

export const ERROR_CODES = {
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT',
  INVALID_TOKEN: 'INVALID_TOKEN',
  TOKEN_EXPIRED: 'TOKEN_EXPIRED',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  SERVER_ERROR: 'SERVER_ERROR',
  NOT_FOUND: 'NOT_FOUND',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN'
} as const;