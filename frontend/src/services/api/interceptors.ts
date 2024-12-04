// src/services/api/interceptors.ts
import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';

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

export const responseErrorInterceptor = (error: AxiosError) => {
  if (error.response) {
    // Handle different error status codes
    switch (error.response.status) {
      case 401:
        // Handle unauthorized - maybe refresh token or redirect to login
        break;
      case 403:
        // Handle forbidden
        break;
      case 404:
        // Handle not found
        break;
      case 500:
        // Handle server error
        break;
    }

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

