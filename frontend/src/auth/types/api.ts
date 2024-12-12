// src/auth/types/api.ts
import type { 
    ApiResponse,
    ApiRequestConfig,
    ApiError,
    ErrorResponse 
  } from '@/common/types/api';
  
  // Auth-specific types
  export interface AuthApiResponse<T = unknown> {
    data: T;
    token?: string;
    refreshToken?: string;
    message?: string;
    status: number;
  }
  
  export interface LoginRequest extends ApiRequestConfig {
    data: {
      email: string;
      password: string;
    };
  }
  
  export interface RegisterRequest extends ApiRequestConfig {
    data: {
      email: string;
      password: string;
      name: string;
    };
  }
  
  // Re-export common types
  export type {
    ApiRequestConfig,
    ApiError,
    ErrorResponse
  } from '@/common/types/api';