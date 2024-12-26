// src/recommendations/providers/RecommendationProvider.tsx
import React, { useState, useCallback } from "react";
import { useDispatch } from "react-redux";
import { RecommendationService } from "../services/recommendationsService";
import { handleApiError } from "../../common/utils/api/apiUtils";
import { RecommendationContext } from "../context/RecommendationsContext";
import { setError, setLoading } from "../store/recommendationsSlice";
import type {
  Recommendation,
  RecommendationFilters,
  RecommendationHistory,
} from "../types/events";

export const RecommendationsProvider: React.FC<{
  children: React.ReactNode;
}> = ({ children }) => {
  const dispatch = useDispatch();

  // State
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [history, setHistory] = useState<RecommendationHistory[]>([]);
  const [filters, setFilters] = useState<RecommendationFilters>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setErrorState] = useState<Error | null>(null);

  // Actions
  const loadRecommendations = useCallback(
    async (pipelineId: string) => {
      setIsLoading(true);
      dispatch(setLoading(true));

      try {
        const data = await RecommendationService.listRecommendations(
          pipelineId,
          filters
        );
        setRecommendations(data);
        setErrorState(null);
      } catch (err) {
        handleApiError(err);
        const errorMessage =
          err instanceof Error ? err.message : "Failed to load recommendations";
        setErrorState(new Error(errorMessage));
        dispatch(setError(errorMessage));
      } finally {
        setIsLoading(false);
        dispatch(setLoading(false));
      }
    },
    [dispatch, filters]
  );

  const applyRecommendation = useCallback(
    async (recommendationId: string, actionId: string) => {
      setIsLoading(true);

      try {
        const historyEntry = await RecommendationService.applyRecommendation(
          recommendationId,
          actionId
        );
        setHistory((prev) => [historyEntry, ...prev]);
        setErrorState(null);
      } catch (err) {
        handleApiError(err);
        const errorMessage =
          err instanceof Error ? err.message : "Failed to apply recommendation";
        setErrorState(new Error(errorMessage));
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const dismissRecommendation = useCallback(
    async (recommendationId: string, reason?: string) => {
      try {
        await RecommendationService.dismissRecommendation(
          recommendationId,
          reason
        );
        setRecommendations((prev) =>
          prev.filter((rec) => rec.id !== recommendationId)
        );
        setErrorState(null);
      } catch (err) {
        handleApiError(err);
        const errorMessage =
          err instanceof Error
            ? err.message
            : "Failed to dismiss recommendation";
        setErrorState(new Error(errorMessage));
      }
    },
    []
  );

  const clearError = useCallback(() => {
    setErrorState(null);
    dispatch(setError(null));
  }, [dispatch]);

  const value = {
    recommendations,
    history,
    filters,
    isLoading,
    error,
    loadRecommendations,
    applyRecommendation,
    dismissRecommendation,
    setFilters,
    clearError,
  };

  return (
    <RecommendationContext.Provider value={value}>
      {children}
    </RecommendationContext.Provider>
  );
};
