// src/decisions/types/models.ts
import type { BaseDecision, DecisionOption, DecisionUrgency, DecisionVote } from './base';

export interface Decision extends BaseDecision {
  options: DecisionOption[];
  selectedOption?: string;
}

export interface DecisionDetails extends Decision {
  analysis?: {
    risks: string[];
    benefits: string[];
    alternatives: string[];
    dependencies?: string[];
  };
  history: DecisionHistoryEntry[];
  votes?: DecisionVote[];
  comments?: DecisionComment[];
}

export interface DecisionHistoryEntry {
  id: string;
  decisionId: string;
  action: 'create' | 'update' | 'vote' | 'comment' | 'apply';
  user: string;
  timestamp: string;
  details: Record<string, unknown>;
  changes?: Array<{
    field: string;
    oldValue: unknown;
    newValue: unknown;
  }>;
}

export interface DecisionComment {
  id: string;
  decisionId: string;
  user: string;
  content: string;
  timestamp: string;
  replyTo?: string;
}

export interface DecisionImpactAnalysis {
  optionId: string;
  risks: Array<{
    description: string;
    severity: DecisionUrgency;
    probability: number;
    mitigation?: string;
  }>;
  benefits: Array<{
    description: string;
    impact: DecisionUrgency;
    confidence: number;
  }>;
  metrics: Record<string, number>;
  recommendations: string[];
}