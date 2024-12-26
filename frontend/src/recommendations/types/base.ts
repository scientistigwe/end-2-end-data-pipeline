// src/recommendations/types/base.ts
export type RecommendationType = 'quality' | 'performance' | 'security' | 'optimization';
export type RecommendationStatus = 'pending' | 'applied' | 'dismissed' | 'failed';

export const RECOMMENDATION_EVENTS = {
  APPLIED: 'recommendation:applied',
  DISMISSED: 'recommendation:dismissed',
  STATUS_CHANGE: 'recommendation:statusChange',
  ERROR: 'recommendation:error'
} as const;
