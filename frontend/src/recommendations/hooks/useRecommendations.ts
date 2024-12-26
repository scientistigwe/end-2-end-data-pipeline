// src/recommendations/hooks/useRecommendations.ts
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { RecommendationService } from '../services/recommendationsService';
import { handleApiError } from '../../common/utils/api/apiUtils';
import { RECOMMENDATION_MESSAGES } from '../constants';
import type { 
  Recommendation, 
  RecommendationFilters 
} from '../types/events';

import { recommendationsApi } from '../api';

interface UseRecommendationsResult {
  recommendations: Recommendation[] | undefined;
  isLoading: boolean;
  error: Error | null;
  applyRecommendation: (recommendationId: string, actionId: string) => Promise<void>;
  dismissRecommendation: (recommendationId: string, reason?: string) => Promise<void>;
  refreshRecommendations: () => Promise<void>;
}

export const useRecommendations = (
  pipelineId: string,
  filters?: RecommendationFilters
): UseRecommendationsResult => {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  const {
    data: recommendations,
    isLoading,
    error: fetchError,
    refetch: refreshRecommendations
  } = useQuery(
    ['recommendations', pipelineId, filters],
    async () => {
      return RecommendationService.listRecommendations(pipelineId, filters);
    },
    {
      refetchInterval: 30000,
      staleTime: 10000
    }
  );

  const { mutateAsync: applyRecommendation } = useMutation(
    async ({ recommendationId, actionId }: { recommendationId: string; actionId: string }) => {
      try {
        return await RecommendationService.applyRecommendation(recommendationId, actionId);
      } catch (error) {
        handleApiError(error);
        throw new Error(RECOMMENDATION_MESSAGES.ERRORS.APPLY_FAILED);
      }
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['recommendations', pipelineId]);
      }
    }
  );

  const { mutateAsync: dismissRecommendation } = useMutation(
    async ({ recommendationId, reason }: { recommendationId: string; reason?: string }) => {
      try {
        // Make sure this method exists in RecommendationService
        const response = await recommendationsApi.dismissRecommendation(recommendationId, reason);
        return response.data;
      } catch (error) {
        handleApiError(error);
        throw new Error(RECOMMENDATION_MESSAGES.ERRORS.DISMISS_FAILED);
      }
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['recommendations', pipelineId]);
      }
    }
  );

  const handleApplyRecommendation = async (recommendationId: string, actionId: string) => {
    await applyRecommendation({ recommendationId, actionId });
  };

  const handleDismissRecommendation = async (recommendationId: string, reason?: string) => {
    await dismissRecommendation({ recommendationId, reason });
  };

  return {
    recommendations,
    isLoading,
    error: fetchError as Error | null,
    applyRecommendation: handleApplyRecommendation,
    dismissRecommendation: handleDismissRecommendation,
    refreshRecommendations
  };
};