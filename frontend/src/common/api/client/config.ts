import {
  ApiRequestConfig,
  BaseApiConfig,
  RetryConfig,
  HTTP_STATUS,
  CONTENT_TYPES
} from '../../types/api';

// Type definitions
export interface ApiConfig {
  readonly BASE_URL: string;
  readonly VERSION: string;
  readonly FULL_BASE_URL: string;
  readonly TIMEOUT: number;
  readonly RETRY_COUNT: number;
  readonly DEFAULT_HEADERS: Readonly<Record<string, string>>;
  readonly CORS: {
    readonly withCredentials: boolean;
    readonly credentials: 'include';
  };
  readonly UPLOAD: {
    readonly MAX_SIZE: number;
    readonly SUPPORTED_FORMATS: readonly string[];
    readonly CHUNK_SIZE: number;
  };
}

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

export interface ValidationError {
  field: string;
  message: string;
  code: string;
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

export interface PaginationParams {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  search?: string;
  filters?: Record<string, string | number | boolean | null>;
}

// Environment configuration
const isDevelopment = import.meta.env.MODE === 'development';

// API Base Configuration
export const API_CONFIG: BaseApiConfig = {
  BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:5000',
  VERSION: 'v1',
  get FULL_BASE_URL() {
    return `${this.BASE_URL}/api/${this.VERSION}`;
  },
  TIMEOUT: 30000,
  RETRY_COUNT: 3,
  DEFAULT_HEADERS: {
    'Content-Type': CONTENT_TYPES.JSON,
    'Accept': CONTENT_TYPES.JSON,
    'X-Requested-With': 'XMLHttpRequest'
  },
  CORS: {
    withCredentials: true,
    credentials: 'include'
  },
  UPLOAD: {
    MAX_SIZE: 50 * 1024 * 1024, // 50MB
    SUPPORTED_FORMATS: [
      'image/jpeg',
      'image/png',
      'image/gif',
      'application/pdf',
      'text/csv',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel'
    ],
    CHUNK_SIZE: 1024 * 1024 * 5 // 5MB chunks
  }
} as const;

// Configuration Objects
export const DEFAULT_REQUEST_CONFIG: Readonly<Partial<ApiRequestConfig>> = {
  withCredentials: true,
  responseType: 'json',
  timeout: API_CONFIG.TIMEOUT
} as const;

export const RETRY_CONFIG: RetryConfig = {
  count: API_CONFIG.RETRY_COUNT,
  delay: 1000,
  statuses: [
    HTTP_STATUS.REQUEST_TIMEOUT,
    HTTP_STATUS.TOO_MANY_REQUESTS,
    HTTP_STATUS.INTERNAL_SERVER_ERROR,
    HTTP_STATUS.BAD_GATEWAY,
    HTTP_STATUS.SERVICE_UNAVAILABLE,
    HTTP_STATUS.GATEWAY_TIMEOUT
  ],
  methods: ['GET', 'HEAD', 'OPTIONS', 'PUT', 'DELETE'],
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

// Error code constants
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

// Type exports for error codes
export type ErrorCode = keyof typeof ERROR_CODES;
export type ContentType = keyof typeof CONTENT_TYPES;