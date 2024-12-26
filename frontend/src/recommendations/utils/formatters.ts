// src/recommendations/utils/formatters.ts
import { dateUtils } from '../../common/utils/date/dateUtils';
import type {
  Recommendation,
  RecommendationType,
  RecommendationStatus
} from '../types/events';
import {
  RECOMMENDATION_TYPE_LABELS,
  RECOMMENDATION_STATUS_LABELS
} from '../constants';

export const formatRecommendationType = (type: RecommendationType): string => {
  return RECOMMENDATION_TYPE_LABELS[type] || type;
};

export const formatRecommendationStatus = (status: RecommendationStatus): string => {
  return RECOMMENDATION_STATUS_LABELS[status] || status;
};

export const formatConfidence = (confidence: number): string => {
  return `${confidence.toFixed(1)}%`;
};

export const formatRecommendationSummary = (recommendation: Recommendation): string => {
  const formattedDate = dateUtils.formatDate(recommendation.createdAt);
  return `${formatRecommendationType(recommendation.type)} - ${recommendation.title} (${formatConfidence(recommendation.confidence)}) - Created: ${formattedDate}`;
};



