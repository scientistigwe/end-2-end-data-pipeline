// src/settings/types/responses.ts
import type { UserSettings, ValidationResult } from './models';

// Define the API response structure
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
}

// Define what the server actually returns
export interface ServerResponse<T> {
  data: ApiResponse<T>;
}

export type SettingsResponse = ServerResponse<UserSettings>;
export type SettingsValidationResponse = ServerResponse<ValidationResult>;