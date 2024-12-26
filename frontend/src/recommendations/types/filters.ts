// src/recommendations/types/filters.ts
import type { ImpactLevel } from '@/common';
import type { RecommendationType, RecommendationStatus } from './base';

export interface RecommendationFilters {
  priority?: string[];
  startDate?: string;
  endDate?: string;
  types?: RecommendationType[];
  impact?: ImpactLevel[];
  status?: RecommendationStatus[];
  minConfidence?: number;
}