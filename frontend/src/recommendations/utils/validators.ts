// src/recommendations/utils/validation.ts
import type { Recommendation } from '../types/events';

export const validateRecommendation = (
  data: Partial<Recommendation>
): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (!data.title?.trim()) {
    errors.push('Title is required');
  }

  if (!data.description?.trim()) {
    errors.push('Description is required');
  }

  if (!data.type) {
    errors.push('Recommendation type is required');
  }

  if (!data.impact) {
    errors.push('Impact level is required');
  }

  if (typeof data.confidence !== 'number' || data.confidence < 0 || data.confidence > 100) {
    errors.push('Confidence must be a number between 0 and 100');
  }

  if (!data.actions || data.actions.length === 0) {
    errors.push('At least one action is required');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
};
