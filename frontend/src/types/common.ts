// src/types/common.ts
export type UserRole = 'user' | 'admin' | 'manager';
export type ImpactLevel = 'high' | 'medium' | 'low';
export type ExportFormat = 'pdf' | 'csv' | 'json';
export type Severity = 'high' | 'medium' | 'low';

export interface TimeRange {
  start: string;
  end: string;
}