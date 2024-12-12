// src/types/recommendations.ts
import { ImpactLevel } from '../../common/types/common';

export type RecommendationType = 'quality' | 'performance' | 'security' | 'optimization';
export type RecommendationStatus = 'pending' | 'applied' | 'dismissed' | 'failed';

export interface Recommendation {
  id: string;
  pipelineId: string;
  type: RecommendationType;
  title: string;
  description: string;
  impact: ImpactLevel;
  confidence: number;
  status: RecommendationStatus;
  source: string;
  createdAt: string;
  updatedAt: string;
  appliedAt?: string;
  metadata?: Record<string, unknown>;
  actions: RecommendationAction[];
}

export interface RecommendationAction {
  id: string;
  type: string;
  description: string;
  automaticApplicable: boolean;
  requiresConfirmation: boolean;
  parameters?: Record<string, unknown>;
  estimatedDuration?: number;
  risks?: string[];
}

export interface RecommendationHistory {
  id: string;
  recommendationId: string;
  pipelineId: string;
  action: RecommendationAction;
  appliedAt: string;
  status: 'success' | 'failed';
  error?: string;
  result?: Record<string, unknown>;
}

export interface RecommendationFilters {
  types?: RecommendationType[];
  impact?: ImpactLevel[];
  status?: RecommendationStatus[];
  minConfidence?: number;
}

export interface RecommendationsState {
  items: Array<{
    id: string;
    type: 'performance' | 'security' | 'cost' | 'reliability';
    title: string;
    description: string;
    impact: 'high' | 'medium' | 'low';
    effort: 'high' | 'medium' | 'low';
    status: 'pending' | 'implementing' | 'completed' | 'dismissed';
    metadata: {
      createdAt: string;
      updatedAt: string;
      implementedAt?: string;
    };
  }>;
  filters: {
    types?: string[];
    impact?: string[];
    status?: string[];
  };
  isLoading: boolean;
  error: string | null;
}
