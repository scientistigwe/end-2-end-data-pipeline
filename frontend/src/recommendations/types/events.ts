// src/recommendations/types/events.ts
import type { RecommendationHistory } from './models';
import { RECOMMENDATION_EVENTS } from './base';

// Keep the event name type here only
export type RecommendationEventName = keyof typeof RECOMMENDATION_EVENTS;

export interface RecommendationError extends Error {
  name: 'RecommendationError';
  code?: string;
  timestamp: string;
  component: 'recommendation';
  details?: unknown;
}

export interface RecommendationAppliedDetail {
  recommendationId: string;
  actionId: string;
  result: RecommendationHistory;
}

export interface RecommendationDismissedDetail {
  recommendationId: string;
  reason?: string;
}

export interface RecommendationStatusChangeDetail {
  recommendationId: string;
  status: string;
  previousStatus?: string;
}

export interface RecommendationErrorDetail {
  error: string;
  code?: string;
}

export type RecommendationEventMap = {
  [RECOMMENDATION_EVENTS.APPLIED]: CustomEvent<RecommendationAppliedDetail>;
  [RECOMMENDATION_EVENTS.DISMISSED]: CustomEvent<RecommendationDismissedDetail>;
  [RECOMMENDATION_EVENTS.STATUS_CHANGE]: CustomEvent<RecommendationStatusChangeDetail>;
  [RECOMMENDATION_EVENTS.ERROR]: CustomEvent<RecommendationErrorDetail>;
};