// src/recommendations/context/RecommendationContext.tsx
import { createContext, useContext } from 'react';
import type {
  Recommendation,
  RecommendationFilters,
  RecommendationHistory
} from '../types/recommendations';

interface RecommendationContextValue {
  // State
  recommendations: Recommendation[];
  history: RecommendationHistory[];
  filters: RecommendationFilters;
  isLoading: boolean;
  error: Error | null;

  // Actions
  loadRecommendations: (pipelineId: string) => Promise<void>;
  applyRecommendation: (recommendationId: string, actionId: string) => Promise<void>;
  dismissRecommendation: (recommendationId: string, reason?: string) => Promise<void>;
  setFilters: (filters: RecommendationFilters) => void;
  clearError: () => void;
}

export const RecommendationContext = createContext<RecommendationContextValue | undefined>(undefined);

export const useRecommendationContext = () => {
  const context = useContext(RecommendationContext);
  if (!context) {
    throw new Error('useRecommendationContext must be used within RecommendationProvider');
  }
  return context;
};