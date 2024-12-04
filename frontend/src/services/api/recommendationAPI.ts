// src/services/recommendationApi.ts
import { api } from './api/client';
import { API_CONFIG } from './api/config';
import { RecommendationAction } from '../types/recommendations';

export const recommendationApi = {
  getRecommendations: async (pipelineId: string) => {
    return api.get(API_CONFIG.ENDPOINTS.RECOMMENDATIONS.LIST, { pipelineId });
  },

  applyRecommendation: async (recommendationId: string, action: RecommendationAction) => {
    return api.post(API_CONFIG.ENDPOINTS.RECOMMENDATIONS.APPLY, {
      recommendationId,
      action
    });
  },

  getRecommendationStatus: async (recommendationId: string) => {
    return api.get(API_CONFIG.ENDPOINTS.RECOMMENDATIONS.STATUS, { id: recommendationId });
  }
};

