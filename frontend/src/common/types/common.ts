// src/common/types/common.ts
import { DataStatus } from './status';

// Enums and Constants
export const IMPACT_LEVELS = ['high', 'medium', 'low'] as const;
export const PRIORITY_LEVELS = ['high', 'medium', 'low'] as const;
export const SORT_DIRECTIONS = ['asc', 'desc'] as const;

// Basic Types
export type ImpactLevel = typeof IMPACT_LEVELS[number];
export type Priority = typeof PRIORITY_LEVELS[number];
export type SortDirection = typeof SORT_DIRECTIONS[number];

// Re-export DataStatus for convenience
export type { DataStatus } from './status';

// Interfaces
export interface TimeRange {
  start: string;
  end: string;
}

export interface Breadcrumb {
  label: string;
  path: string;
  icon?: string;
}

export interface SelectOption<T = string> {
  label: string;
  value: T;
  disabled?: boolean;
  icon?: string;
}

export interface FilterConfig {
  field: string;
  operator: 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte' | 'contains' | 'in';
  value: unknown;
}

// Impact Related Types
export interface ImpactMetrics {
  level: ImpactLevel;
  score: number;
  confidence: number;
}

export interface ImpactAssessment {
  level: ImpactLevel;
  description: string;
  metrics?: ImpactMetrics;
  recommendations?: string[];
}

// Utility Types
export type LevelMapping = Record<ImpactLevel, number>;

// Common Type Guards
export const isImpactLevel = (value: unknown): value is ImpactLevel => {
  return typeof value === 'string' && IMPACT_LEVELS.includes(value as ImpactLevel);
};

// Common Constants for Impact Levels
export const IMPACT_LEVEL_WEIGHTS: LevelMapping = {
  high: 3,
  medium: 2,
  low: 1
};

export const IMPACT_LEVEL_LABELS: Record<ImpactLevel, string> = {
  high: 'High Impact',
  medium: 'Medium Impact',
  low: 'Low Impact'
};

// Common Color Mappings for Impact Levels
export const IMPACT_LEVEL_COLORS: Record<ImpactLevel, { bg: string; text: string }> = {
  high: { bg: 'bg-red-100', text: 'text-red-800' },
  medium: { bg: 'bg-yellow-100', text: 'text-yellow-800' },
  low: { bg: 'bg-green-100', text: 'text-green-800' }
};