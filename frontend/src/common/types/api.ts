// frontend\src\common\types\api.ts
import type { 
  AxiosProgressEvent, 
  AxiosRequestConfig, 
  InternalAxiosRequestConfig, 
  ResponseType,
  AxiosHeaderValue,
  RawAxiosRequestHeaders
} from 'axios';

// HTTP Status Codes
export const enum HTTP_STATUS {
  OK = 200,
  CREATED = 201,
  ACCEPTED = 202,
  NO_CONTENT = 204,
  MULTIPLE_CHOICES = 300,
  BAD_REQUEST = 400,
  UNAUTHORIZED = 401,
  FORBIDDEN = 403,
  NOT_FOUND = 404,
  METHOD_NOT_ALLOWED = 405,
  CONFLICT = 409,
  UNPROCESSABLE_ENTITY = 422,
  LOCKED = 423,
  TOO_MANY_REQUESTS = 429,
  INTERNAL_SERVER_ERROR = 500,
  BAD_GATEWAY = 502,
  SERVICE_UNAVAILABLE = 503,
  REQUEST_TIMEOUT = 408,
  GATEWAY_TIMEOUT = 504,
  RATE_LIMIT_EXCEEDED = 429
}

// HTTP Method Types
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS';

// Retry Configuration Types
export type RetryStatus = 
  | HTTP_STATUS.REQUEST_TIMEOUT
  | HTTP_STATUS.TOO_MANY_REQUESTS
  | HTTP_STATUS.INTERNAL_SERVER_ERROR
  | HTTP_STATUS.BAD_GATEWAY
  | HTTP_STATUS.SERVICE_UNAVAILABLE
  | HTTP_STATUS.GATEWAY_TIMEOUT;

export interface RetryConfig {
  readonly count: number;
  readonly delay: number;
  readonly statuses: readonly RetryStatus[];
  readonly methods: readonly HttpMethod[];
  readonly backoffFactor: number;
  readonly maxDelay: number;
}

// Request Configuration Types
export interface RetryableRequestConfig<T = any> extends InternalAxiosRequestConfig<T> {
  _retry?: number;
}

export interface ApiRequestConfig extends Omit<AxiosRequestConfig, 'url' | 'method' | 'data'> {
  routeParams?: Record<string, string>;
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void;
  onDownloadProgress?: (progressEvent: AxiosProgressEvent) => void;
  withCredentials?: boolean;
  responseType?: ResponseType;
  signal?: AbortSignal;
  headers?: RawAxiosRequestHeaders;
}

export interface BaseApiConfig {
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

// Response Types
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

export interface ApiResponse<T = unknown> extends ApiSuccessResponse<T> {}

export interface SuccessResponse extends ApiResponse<null> {
  success: true;
}

// Error Types
export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

export interface ApiError {
  code: string;
  message: string;
  status?: number;
  details?: unknown;
  validationErrors?: ValidationError[];
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

// Bulk Operation Types
export interface BulkOperationResponse extends ApiResponse<{
  succeeded: number;
  failed: number;
  errors?: ApiError[];
}> {}

// Cache Types
export interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

export type HeadersType = Record<string, AxiosHeaderValue>;

// Utility Types
export type ApiErrorFormatter = (error: unknown) => ApiError;

// Content Types
export const enum CONTENT_TYPES {
  JSON = 'application/json',
  FORM_DATA = 'multipart/form-data',
  FORM_URLENCODED = 'application/x-www-form-urlencoded',
  TEXT = 'text/plain',
  HTML = 'text/html',
  XML = 'application/xml',
  BINARY = 'application/octet-stream'
}

// Error Codes
export const enum ERROR_CODES {
  NETWORK_ERROR = 'NETWORK_ERROR',
  TIMEOUT = 'TIMEOUT',
  INVALID_TOKEN = 'INVALID_TOKEN',
  TOKEN_EXPIRED = 'TOKEN_EXPIRED',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  NOT_FOUND = 'NOT_FOUND',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE',
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED'
}

