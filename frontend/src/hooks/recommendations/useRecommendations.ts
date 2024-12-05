// src/hooks/recommendations/useRecommendations.ts
import { useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { recommendationsApi } from '../../services/api/recommendationsAPI';
import { handleApiError } from '../../utils/helpers/apiUtils';
import {
  setRecommendations,
  updateRecommendation,
  setRecommendationHistory,
  addHistoryEntry,
  setLoading,
  setError
} from '../../store/recommendations/recommendationsSlice';
import type { RecommendationFilters } from '../../types/recommendations';

export function useRecommendations(pipelineId: string) {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  // Fetch recommendations
  const { data: recommendations, refetch: refreshRecommendations } = useQuery(
    ['recommendations', pipelineId],
    async () => {
      dispatch(setLoading(true));
      try {
        const response = await recommendationsApi.getRecommendations(pipelineId);
        dispatch(setRecommendations(response.data));
        return response.data;
      } catch (error) {
        handleApiError(error);
        throw error;
      } finally {
        dispatch(setLoading(false));
      }
    }
  );

  // Apply recommendation
  const { mutate: applyRecommendation } = useMutation(
    async ({
      recommendationId,
      actionId,
      parameters
    }: {
      recommendationId: string;
      actionId: string;
      parameters?: Record<string, unknown>;
    }) => {
      const response = await recommendationsApi.applyRecommendation(
        recommendationId,
        actionId,
        parameters
      );
      dispatch(addHistoryEntry({
        pipelineId,
        entry: response.data
      }));
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['recommendations', pipelineId]);
      },
      onError: handleApiError
    }
  );

  // Dismiss recommendation
  const { mutate: dismissRecommendation } = useMutation(
    async ({
      recommendationId,
      reason
    }: {
      recommendationId: string;
      reason?: string;
    }) => {
      await recommendationsApi.dismissRecommendation(recommendationId, reason);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['recommendations', pipelineId]);
      },
      onError: handleApiError
    }
  );

  // Fetch recommendation history
  const { data: history } = useQuery(
    ['recommendationHistory', pipelineId],
    async () => {
      const response = await recommendationsApi.getRecommendationHistory(pipelineId);
      dispatch(setRecommendationHistory({
        pipelineId,
        history: response.data
      }));
      return response.data;
    }
  );

  // Filter recommendations
  const filterRecommendations = useCallback((filters: RecommendationFilters) => {
    if (!recommendations) return [];
    
    return recommendations.filter(rec => {
      if (filters.types && !filters.types.includes(rec.type)) return false;
      if (filters.impact && !filters.impact.includes(rec.impact)) return false;
      if (filters.status && !filters.status.includes(rec.status)) return false;
      if (filters.minConfidence && rec.confidence < filters.minConfidence) return false;
      return true;
    });
  }, [recommendations]);

  return {
    recommendations,
    history,
    applyRecommendation,
    dismissRecommendation,
    refreshRecommendations,
    filterRecommendations
  } as const;
}