// src/recommendations/types/types.ts
import type { ImpactLevel } from '@/common';
import type { RecommendationType, RecommendationStatus } from './base';

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