// src/recommendations/pipeline/recommendationService.ts
import { recommendationsApi } from '../api/recommendationsApi';
import { handleApiError } from '../../common/utils/api/apiUtils';
import { dateUtils } from '../../common/utils/date/dateUtils';
import { RECOMMENDATION_MESSAGES } from '../constants';
import type {
  Recommendation,
  RecommendationHistory,
  RecommendationFilters
} from '../types/events';

export class RecommendationService {
  static async listRecommendations(
        pipelineId: string, 
        filters?: RecommendationFilters
      ): Promise<Recommendation[]> {
        try {
          const response = await recommendationsApi.getRecommendations(pipelineId, filters);
          return response.data.map(RecommendationService.transformRecommendation);
        } catch (err) {
          handleApiError(err);
          throw new Error(RECOMMENDATION_MESSAGES.ERRORS.LOAD_FAILED);
        }
      }
    
  static async dismissRecommendation(
        recommendationId: string,
        reason?: string
      ): Promise<void> {
        try {
          await recommendationsApi.dismissRecommendation(recommendationId, reason);
        } catch (err) {
          handleApiError(err);
          throw new Error(RECOMMENDATION_MESSAGES.ERRORS.DISMISS_FAILED);
        }
      }

  static async applyRecommendation(
    recommendationId: string,
    actionId: string,
    parameters?: Record<string, unknown>
  ): Promise<RecommendationHistory> {
    try {
      const response = await recommendationsApi.applyRecommendation(
        recommendationId,
        actionId,
        parameters
      );
      return this.transformHistory(response.data);
    } catch (err) {
      handleApiError(err);
      throw new Error(RECOMMENDATION_MESSAGES.ERRORS.APPLY_FAILED);
    }
  }

  static async getRecommendationHistory(pipelineId: string): Promise<RecommendationHistory[]> {
    try {
      const response = await recommendationsApi.getRecommendationHistory(pipelineId);
      return response.data.map(this.transformHistory);
    } catch (err) {
      handleApiError(err);
      throw new Error(RECOMMENDATION_MESSAGES.ERRORS.FETCH_HISTORY_FAILED);
    }
  }

  private static transformRecommendation(recommendation: Recommendation): Recommendation {
    return {
      ...recommendation,
      createdAt: dateUtils.formatDate(recommendation.createdAt),
      updatedAt: dateUtils.formatDate(recommendation.updatedAt),
      appliedAt: recommendation.appliedAt ? dateUtils.formatDate(recommendation.appliedAt) : undefined
    };
  }

  private static transformHistory(history: RecommendationHistory): RecommendationHistory {
    return {
      ...history,
      appliedAt: dateUtils.formatDate(history.appliedAt)
    };
  }
}

export default RecommendationService;
