// auth/utils/errorHandling.ts
import { AxiosError, AxiosResponse } from 'axios';
import type { ApiErrorData, ValidationErrors } from '../types/auth';

interface ErrorWithResponse {
  response?: {
    data?: unknown;
  };
}

export const isAuthError = (
  error: unknown
): error is AxiosError<ApiErrorData> & { response: AxiosResponse<ApiErrorData> } => {
  if (!(error instanceof Error)) return false;
  if (!('isAxiosError' in error)) return false;
  
  // Check if it has a response with data
  const errorWithResponse = error as ErrorWithResponse;
  if (!errorWithResponse.response) return false;
  if (!errorWithResponse.response.data) return false;

  // Type guard for ApiErrorData
  const responseData = errorWithResponse.response.data;
  if (
    typeof responseData !== 'object' || 
    responseData === null || 
    !('success' in responseData)
  ) {
    return false;
  }

  return !responseData.success;
};

export const formatValidationErrors = (details: ValidationErrors): string => {
  if (!details || Object.keys(details).length === 0) return '';
  
  return Object.entries(details)
    .map(([field, messages]) => `${field}: ${messages.join(', ')}`)
    .join('; ');
};


export const getErrorMessage = (error: any): string => {
  if (isAuthError(error)) {
    const { data } = error.response;
    
    if (data.error?.details) {
      return `Validation failed: ${formatValidationErrors(data.error.details)}`;
    }
    
    if (data.message) {
      return data.message;
    }
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  if (!error) return 'An unknown error occurred';

  // Handle axios error responses
  if (error.response) {
    const { status, data } = error.response;
    
    if (status === 409) {
      return 'An account with this email already exists';
    }
    
    if (data?.error?.details) {
      if (typeof data.error.details === 'string') {
        return data.error.details;
      }
      return Object.entries(data.error.details)
        .map(([field, errors]) => `${field}: ${errors.join(', ')}`)
        .join('; ');
    }
    
    if (data?.error?.message) {
      return data.error.message;
    }
  }

  // Handle other error types
  if (error.message) {
    return error.message;
  }

  return 'An unexpected error occurred';
};

export function handleApiError(error: unknown): Error {
  if (isAuthError(error)) {
      const errorResponse = error.response.data;
      if (errorResponse.error?.details) {
          return new Error(formatValidationErrors(errorResponse.error.details));
      }
      return new Error(errorResponse.message || 'An unexpected error occurred');
  }
  return error instanceof Error ? error : new Error('An unexpected error occurred');
}
