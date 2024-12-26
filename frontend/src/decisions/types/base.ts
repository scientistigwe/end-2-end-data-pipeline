// src/decisions/types/base.ts
import type { ImpactLevel } from '@/common';

export type DecisionType = 'quality' | 'pipeline' | 'security';
export type DecisionStatus = 'pending' | 'completed' | 'deferred' | 'expired';
export type DecisionUrgency = ImpactLevel;
export type DecisionVote = 'approve' | 'reject' | 'defer';

export interface DecisionOption {
  id: string;
  title: string;
  description: string;
  impact: ImpactLevel;
  consequences: string[];
  requirements?: string[];
  estimatedEffort?: string;
  automaticApplicable: boolean;
}

export interface BaseDecision {
  id: string;
  type: DecisionType;
  title: string;
  description: string;
  urgency: DecisionUrgency;
  status: DecisionStatus;
  context: Record<string, unknown>;
  deadline?: string;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  assignedTo?: string[];
  pipelineId: string;
}