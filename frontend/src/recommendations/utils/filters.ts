// src/recommendations/utils/filters.ts
import type { 
    Recommendation, 
    RecommendationFilters 
  } from '../types/recommendations';
  
  export const applyRecommendationFilters = (
    recommendations: Recommendation[],
    filters: RecommendationFilters
  ): Recommendation[] => {
    return recommendations.filter(rec => {
      if (filters.types?.length && !filters.types.includes(rec.type)) {
        return false;
      }
      
      if (filters.impact?.length && !filters.impact.includes(rec.impact)) {
        return false;
      }
      
      if (filters.status?.length && !filters.status.includes(rec.status)) {
        return false;
      }
      
      if (typeof filters.minConfidence === 'number' && rec.confidence < filters.minConfidence) {
        return false;
      }
      
      return true;
    });
  };
  