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

export const getErrorMessage = (error: unknown): string => {
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
  
  return 'An unexpected error occurred';
};