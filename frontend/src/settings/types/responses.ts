// src/settings/types/responses.ts
import type { UserSettings, ValidationResult } from './models';

// Base API response structure
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
}

// Server response wrapper
export interface ServerResponse<T> {
  data: T;  // Remove the ApiResponse wrapper, data is directly the type we want
  message?: string;
  status: number;
}

export type SettingsResponse = ServerResponse<UserSettings>;
export type SettingsValidationResponse = ServerResponse<ValidationResult>;