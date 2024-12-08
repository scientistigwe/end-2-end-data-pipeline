// src/services/api/interceptors.ts
import { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { ErrorResponse } from '../types/api';

export const requestInterceptor = (config: InternalAxiosRequestConfig) => {
  // Get token from storage
  const token = localStorage.getItem('token');

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
};

export const requestErrorInterceptor = (error: AxiosError) => {
  return Promise.reject(error);
};

export const responseInterceptor = (response: AxiosResponse) => {
  // Transform response data if needed
  if (response.data) {
    return response.data;
  }
  return response;
};

export const responseErrorInterceptor = (error: AxiosError<ErrorResponse>) => {
  if (error.response) {
    // ...
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

