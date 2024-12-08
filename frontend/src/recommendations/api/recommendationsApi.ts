// src/recommendations/api/recommendationsApi.ts
import { recommendationsClient } from './client';
import { API_CONFIG } from './config';
import type { ApiResponse } from '../../common/types/api';
import type {
  Recommendation,
  RecommendationHistory,
  RecommendationFilters
} from '../types/recommendations';

export class RecommendationsApi {
  static async getRecommendations(
    pipelineId: string,
    filters?: RecommendationFilters
  ): Promise<ApiResponse<Recommendation[]>> {
    return recommendationsClient.request('get', API_CONFIG.ENDPOINTS.RECOMMENDATIONS.LIST, {
      params: { pipelineId, ...filters }
    });
  }

  static async getRecommendationDetails(
    recommendationId: string
  ): Promise<ApiResponse<Recommendation>> {
    return recommendationsClient.request(
      'get',
      API_CONFIG.ENDPOINTS.RECOMMENDATIONS.DETAILS.replace(':id', recommendationId)
    );
  }

  static async applyRecommendation(
    recommendationId: string,
    actionId: string,
    parameters?: Record<string, unknown>
  ): Promise<ApiResponse<RecommendationHistory>> {
    return recommendationsClient.request(
      'post',
      API_CONFIG.ENDPOINTS.RECOMMENDATIONS.APPLY.replace(':id', recommendationId),
      {},
      { actionId, parameters }
    );
  }

  static async dismissRecommendation(
    recommendationId: string,
    reason?: string
  ): Promise<ApiResponse<void>> {
    return recommendationsClient.request(
      'post',
      API_CONFIG.ENDPOINTS.RECOMMENDATIONS.DISMISS.replace(':id', recommendationId),
      {},
      { reason }
    );
  }

  static async getApplicationStatus(
    recommendationId: string
  ): Promise<ApiResponse<RecommendationHistory>> {
    return recommendationsClient.request(
      'get',
      API_CONFIG.ENDPOINTS.RECOMMENDATIONS.STATUS.replace(':id', recommendationId)
    );
  }

  static async getRecommendationHistory(
    pipelineId: string
  ): Promise<ApiResponse<RecommendationHistory[]>> {
    return recommendationsClient.request(
      'get',
      API_CONFIG.ENDPOINTS.RECOMMENDATIONS.HISTORY.replace(':id', pipelineId)
    );
  }
}
