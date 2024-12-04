// src/utils/apiUtils.ts
import { AxiosError } from 'axios';
import { ApiError, ApiErrorFormatter } from '../../services/api/types';
import { toast } from 'react-hot-toast';

export const formatApiError: ApiErrorFormatter = (error): ApiError => {
  if (error instanceof AxiosError) {
    return {
      code: error.response?.data?.code || error.code || 'UNKNOWN_ERROR',
      message: error.response?.data?.message || error.message,
      status: error.response?.status,
      details: error.response?.data?.details
    };
  }

  if ((error as ApiError).code) {
    return error as ApiError;
  }

  return {
    code: 'UNKNOWN_ERROR',
    message: 'An unexpected error occurred',
    status: 500
  };
};

export const handleApiError = (error: unknown): void => {
  const formattedError = formatApiError(error);
  toast.error(formattedError.message);
};