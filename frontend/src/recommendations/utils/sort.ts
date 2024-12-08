// src/recommendations/utils/sort.ts
import type { Recommendation } from '../types/recommendations';

export const sortRecommendations = (
  recommendations: Recommendation[],
  sortBy: 'confidence' | 'impact' | 'date' = 'confidence'
): Recommendation[] => {
  return [...recommendations].sort((a, b) => {
    switch (sortBy) {
      case 'confidence':
        return b.confidence - a.confidence;
      case 'impact':
        return getImpactWeight(b.impact) - getImpactWeight(a.impact);
      case 'date':
        return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      default:
        return 0;
    }
  });
};

const getImpactWeight = (impact: string): number => {
  switch (impact) {
    case 'high':
      return 3;
    case 'medium':
      return 2;
    case 'low':
      return 1;
    default:
      return 0;
  }
};
