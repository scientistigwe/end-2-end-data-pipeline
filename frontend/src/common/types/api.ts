// common/types/api.ts
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
  GATEWAY_TIMEOUT = 504
}

// Base API Types
export interface ApiResponse<T = unknown> {
  success: boolean;
  message?: string;
  data: T;
  error?: ApiError;
  meta?: ApiMetadata;
  status?: HTTP_STATUS; 
}

export interface ApiMetadata {
  timestamp?: string;
  requestId?: string;
  page?: number;
  limit?: number;
  total?: number;
  totalPages?: number;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  validationErrors?: ValidationError[];
}

export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

export interface ApiErrorResponse {
  success: false;
  message: string;
  error?: ApiError;
}

// Request Configuration
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS';

export interface ApiRequestConfig extends Omit<AxiosRequestConfig, 'url' | 'method' | 'data'> {
  routeParams?: Record<string, string>;
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void;
  onDownloadProgress?: (progressEvent: AxiosProgressEvent) => void;
  withCredentials?: boolean;
  responseType?: ResponseType;
  signal?: AbortSignal;
  headers?: RawAxiosRequestHeaders;
}

export interface RetryableRequestConfig<T = any> extends InternalAxiosRequestConfig<T> {
  _retry?: number;
}

// Retry Configuration
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

// Pagination
export interface PaginationParams {
  page: number;
  limit: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> extends ApiResponse<T> {
  meta: Required<Pick<ApiMetadata, 'page' | 'limit' | 'total' | 'totalPages'>>;
}

// Cache
export interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

export type HeadersType = Record<string, AxiosHeaderValue>;

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
  INVALID_TOKEN = 'TOKEN_INVALID',
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

// Type Guards
export function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    'message' in error
  );
}

export function isApiResponse<T>(response: unknown): response is ApiResponse<T> {
  return (
    typeof response === 'object' &&
    response !== null &&
    'success' in response &&
    'data' in response
  );
}

export function isPaginatedResponse<T>(response: unknown): response is PaginatedResponse<T> {
  return (
    isApiResponse(response) &&
    'meta' in response &&
    typeof response.meta === 'object' &&
    response.meta !== null &&
    'page' in response.meta &&
    'limit' in response.meta &&
    'total' in response.meta &&
    'totalPages' in response.meta
  );
}