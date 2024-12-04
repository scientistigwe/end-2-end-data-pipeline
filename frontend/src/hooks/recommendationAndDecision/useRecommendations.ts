```typescript
// src/hooks/recommendations/useRecommendations.ts
import { useState, useCallback } from 'react';
import { useQuery, useMutation } from 'react-query';
import { recommendationApi } from '../../services/recommendationApi';
import { handleApiError } from '../../utils/apiUtils';

interface Recommendation {
  id: string;
  type: 'quality' | 'performance' | 'security' | 'optimization';
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  confidence: number;
  source: string;
  metadata: Record<string, any>;
  possibleActions: RecommendationAction[];
}

interface RecommendationAction {
  id: string;
  type: string;
  description: string;
  automaticApplicable: boolean;
  requiresConfirmation: boolean;
  parameters?: Record<string, any>;
}

export const useRecommendations = (pipelineId: string) => {
  const [selectedRecommendation, setSelectedRecommendation] = useState<string | null>(null);

  // Get Recommendations
  const { data: recommendations, refetch: refreshRecommendations } = useQuery<Recommendation[]>(
    ['recommendations', pipelineId],
    () => recommendationApi.getRecommendations(pipelineId),
    {
      refetchInterval: 5000,
      enabled: !!pipelineId
    }
  );

  // Get Recommendation Details
  const { data: recommendationDetails } = useQuery(
    ['recommendationDetails', selectedRecommendation],
    () => recommendationApi.getRecommendationDetails(selectedRecommendation!),
    {
      enabled: !!selectedRecommendation
    }
  );

  // Apply Recommendation
  const { mutate: applyRecommendation, isLoading: isApplying } = useMutation(
    async ({ recommendationId, actionId, parameters }: {
      recommendationId: string;
      actionId: string;
      parameters?: Record<string, any>;
    }) => {
      return recommendationApi.applyRecommendation(recommendationId, actionId, parameters);
    },
    {
      onSuccess: () => {
        refreshRecommendations();
      },
      onError: (error) => handleApiError(error)
    }
  );

  // Dismiss Recommendation
  const { mutate: dismissRecommendation } = useMutation(
    async (recommendationId: string) => {
      return recommendationApi.dismissRecommendation(recommendationId);
    },
    {
      onSuccess: () => {
        refreshRecommendations();
      }
    }
  );

  // Get Applied Recommendations History
  const { data: history } = useQuery(
    ['recommendationsHistory', pipelineId],
    () => recommendationApi.getRecommendationsHistory(pipelineId),
    {
      enabled: !!pipelineId
    }
  );

  return {
    recommendations,
    recommendationDetails,
    selectedRecommendation,
    setSelectedRecommendation,
    applyRecommendation,
    dismissRecommendation,
    refreshRecommendations,
    history,
    isApplying
  };
};
