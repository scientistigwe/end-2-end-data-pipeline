// src/types/decisions.ts
import { ImpactLevel } from '../../common/types/common';

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

export interface Decision {
  id: string;
  type: DecisionType;
  title: string;
  description: string;
  urgency: DecisionUrgency;
  status: DecisionStatus;
  options: DecisionOption[];
  context: Record<string, unknown>;
  deadline?: string;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  assignedTo?: string[];
  selectedOption?: string;
  pipelineId: string;
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
  changes?: {
    field: string;
    oldValue: unknown;
    newValue: unknown;
  }[];
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
    severity: ImpactLevel;
    probability: number;
    mitigation?: string;
  }>;
  benefits: Array<{
    description: string;
    impact: ImpactLevel;
    confidence: number;
  }>;
  metrics: Record<string, number>;
  recommendations: string[];
}

export interface DecisionFilters {
  types?: DecisionType[];
  status?: DecisionStatus[];
  urgency?: DecisionUrgency[];
  assignedTo?: string[];
  dateRange?: {
    start: string;
    end: string;
  };
}

export interface DateRange {
  start?: string;
  end?: string;
}

export interface DecisionFilterOptions {
  types?: DecisionType[];
  status?: DecisionStatus[];
  urgency?: DecisionUrgency[];
  assignedTo?: string[];
  dateRange?: DateRange;
}

export interface DecisionState {
  decisions: Record<string, {
    id: string;
    title: string;
    type: string;
    status: 'pending' | 'approved' | 'rejected' | 'implemented';
    urgency: 'high' | 'medium' | 'low';
    description: string;
    assignedTo: string[];
    metadata: {
      createdAt: string;
      updatedAt: string;
      implementedAt?: string;
      rationale: string;
      stakeholders: string[];
    };
    alternatives: Array<{
      id: string;
      description: string;
      pros: string[];
      cons: string[];
    }>;
    impact: {
      areas: Array<{
        name: string;
        impact: 'high' | 'medium' | 'low';
        description: string;
      }>;
      risks: Array<{
        description: string;
        likelihood: 'high' | 'medium' | 'low';
        mitigation: string;
      }>;
    };
    documents: Array<{
      id: string;
      name: string;
      url: string;
    }>;
  }>;
  history: Array<{
    id: string;
    decisionId: string;
    type: 'creation' | 'update' | 'status_change' | 'assignment';
    changes: Record<string, unknown>;
    timestamp: string;
    userId: string;
  }>;
  filters: {
    types?: string[];
    status?: string[];
    urgency?: string[];
    assignedTo?: string[];
    dateRange?: {
      start: string;
      end: string;
    };
  };
  selectedDecisionId: string | null;
  isLoading: boolean;
  error: string | null;
}

