// src/recommendations/constants.ts

// Core Configuration
export const RECOMMENDATION_CONFIG = {
  MIN_CONFIDENCE: 0,
  MAX_CONFIDENCE: 100,
  REFRESH_INTERVAL: 30000,
  STALE_TIME: 10000,
  MAX_ACTIONS: 5
} as const;

// Types and Statuses
export const RECOMMENDATION_TYPES = [
  'quality',
  'performance',
  'security',
  'optimization'
] as const;

export const RECOMMENDATION_STATUSES = [
  'pending',
  'applied',
  'dismissed',
  'failed'
] as const;

// Type Definitions
export type RecommendationType = typeof RECOMMENDATION_TYPES[number];
export type RecommendationStatus = typeof RECOMMENDATION_STATUSES[number];

// Labels and Display Text
export const RECOMMENDATION_TYPE_LABELS: Record<RecommendationType, string> = {
  quality: 'Quality',
  performance: 'Performance',
  security: 'Security',
  optimization: 'Optimization'
};

export const RECOMMENDATION_STATUS_LABELS: Record<RecommendationStatus, string> = {
  pending: 'Pending',
  applied: 'Applied',
  dismissed: 'Dismissed',
  failed: 'Failed'
};

// Messages
export const RECOMMENDATION_MESSAGES = {
  ERRORS: {
    LOAD_FAILED: 'Failed to load recommendations',
    APPLY_FAILED: 'Failed to apply recommendation',
    DISMISS_FAILED: 'Failed to dismiss recommendation',
    FETCH_HISTORY_FAILED: 'Failed to fetch recommendation history',
    VALIDATION_FAILED: 'Invalid recommendation data'
  },
  SUCCESS: {
    APPLIED: 'Recommendation applied successfully',
    DISMISSED: 'Recommendation dismissed'
  }
} as const;

// Status Colors
export const STATUS_COLORS: Record<RecommendationStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  applied: 'bg-green-100 text-green-800',
  dismissed: 'bg-gray-100 text-gray-800',
  failed: 'bg-red-100 text-red-800'
};