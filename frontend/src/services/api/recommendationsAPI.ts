// src/services/api/recommendationsApi.ts
import { BaseApiClient } from './c
lient';
import { API_CONFIG } from './config';
import type { ApiResponse } from '../../types/api';
import type {
  Recommendation,
  RecommendationHistory,
  RecommendationFilters
} from '../../types/recommendations';

class RecommendationsApi extends BaseApiClient {
  /**
   * Get recommendations for a pipeline
   */
  async getRecommendations(
    pipelineId: string,
    filters?: RecommendationFilters
  ): Promise<ApiResponse<Recommendation[]>> {
    return this.request('get', API_CONFIG.ENDPOINTS.RECOMMENDATIONS.LIST, {
      routeParams: { id: pipelineId },
      params: filters
    });
  }

  /**
   * Get detailed information about a recommendation
   */
  async getRecommendationDetails(
    recommendationId: string
  ): Promise<ApiResponse<Recommendation>> {
    return this.request('get', API_CONFIG.ENDPOINTS.RECOMMENDATIONS.DETAILS, {
      routeParams: { id: recommendationId }
    });
  }

  /**
   * Apply a recommendation
   */
  async applyRecommendation(
    recommendationId: string,
    actionId: string,
    parameters?: Record<string, unknown>
  ): Promise<ApiResponse<RecommendationHistory>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.RECOMMENDATIONS.APPLY,
      {
        routeParams: { id: recommendationId }
      },
      { actionId, parameters }
    );
  }

  /**
   * Get the status of an applied recommendation
   */
  async getApplicationStatus(
    recommendationId: string
  ): Promise<ApiResponse<RecommendationHistory>> {
    return this.request('get', API_CONFIG.ENDPOINTS.RECOMMENDATIONS.STATUS, {
      routeParams: { id: recommendationId }
    });
  }

  /**
   * Dismiss a recommendation
   */
  async dismissRecommendation(
    recommendationId: string,
    reason?: string
  ): Promise<ApiResponse<void>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.RECOMMENDATIONS.DISMISS,
      {
        routeParams: { id: recommendationId }
      },
      { reason }
    );
  }

  /**
   * Get recommendation history for a pipeline
   */
  async getRecommendationHistory(
    pipelineId: string
  ): Promise<ApiResponse<RecommendationHistory[]>> {
    return this.request('get', API_CONFIG.ENDPOINTS.RECOMMENDATIONS.HISTORY, {
      routeParams: { id: pipelineId }
    });
  }
}

export const recommendationsApi = new RecommendationsApi();