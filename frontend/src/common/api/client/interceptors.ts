// src/services/api/interceptors.ts
import { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { ApiErrorResponse } from '@/common/types/api';

export const requestInterceptor = (config: InternalAxiosRequestConfig) => {
  // Ensure credentials are always included
  config.withCredentials = true;
  return config;
};

export const responseInterceptor = (response: AxiosResponse) => {
  if (response.data) {
    return response.data;
  }
  return response;
};

export const responseErrorInterceptor = (error: AxiosError<ApiErrorResponse>) => {
  if (error.response) {
    return Promise.reject({
      code: error.response.status,
      message: error.response.data?.message || 'An error occurred',
      details: error.response.data
    });
  }

  return Promise.reject({
    code: 'NETWORK_ERROR',
    message: 'Network error occurred'
  });
};