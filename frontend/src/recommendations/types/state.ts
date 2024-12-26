// src/recommendations/types/state.ts
export interface RecommendationsState {
    items: Array<RecommendationStateItem>;
    filters: RecommendationStateFilters;
    isLoading: boolean;
    error: string | null;
  }
  
  export interface RecommendationStateItem {
    id: string;
    type: 'performance' | 'security' | 'cost' | 'reliability';
    title: string;
    description: string;
    impact: 'high' | 'medium' | 'low';
    effort: 'high' | 'medium' | 'low';
    status: 'pending' | 'implementing' | 'completed' | 'dismissed';
    metadata: RecommendationMetadata;
  }
  
  export interface RecommendationMetadata {
    createdAt: string;
    updatedAt: string;
    implementedAt?: string;
  }
  
  export interface RecommendationStateFilters {
    types?: string[];
    impact?: string[];
    status?: string[];
  }