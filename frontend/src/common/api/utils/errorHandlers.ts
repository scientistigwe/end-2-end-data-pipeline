// src/common/api/utils/errorHandlers.ts
import { AxiosError } from 'axios';
import type { ApiError } from '@/common/types/api';

export const handleApiError = (error: unknown): ApiError => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ message: string }>;
    return {
      code: axiosError.code || 'UNKNOWN_ERROR',
      message: axiosError.response?.data?.message || axiosError.message,
      status: axiosError.response?.status,
      details: axiosError.response?.data
    };
  }

  if (error instanceof Error) {
    return {
      code: 'APP_ERROR',
      message: error.message,
      details: error
    };
  }

  return {
    code: 'UNKNOWN_ERROR',
    message: 'An unknown error occurred',
    details: error
  };
};



