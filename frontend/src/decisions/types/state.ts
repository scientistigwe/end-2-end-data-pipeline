// src/decisions/types/state.ts
import type { DecisionType, DecisionStatus, DecisionUrgency } from './base';
import type { DecisionFilters } from './filters';

export interface DecisionState {
  decisions: Record<string, DecisionStateEntry>;
  history: DecisionStateHistory[];
  filters: DecisionFilters;
  selectedDecisionId: string | null;
  isLoading: boolean;
  error: string | null;
}

export interface DecisionStateEntry {
  id: string;
  title: string;
  type: string;
  status: DecisionStatus;
  urgency: DecisionUrgency;
  description: string;
  assignedTo: string[];
  metadata: DecisionMetadata;
  alternatives: DecisionAlternative[];
  impact: DecisionImpact;
  documents: DecisionDocument[];
}

export interface DecisionMetadata {
  createdAt: string;
  updatedAt: string;
  implementedAt?: string;
  rationale: string;
  stakeholders: string[];
}

export interface DecisionAlternative {
  id: string;
  description: string;
  pros: string[];
  cons: string[];
}

export interface DecisionImpact {
  areas: Array<{
    name: string;
    impact: DecisionUrgency;
    description: string;
  }>;
  risks: Array<{
    description: string;
    likelihood: DecisionUrgency;
    mitigation: string;
  }>;
}

export interface DecisionDocument {
  id: string;
  name: string;
  url: string;
}

export interface DecisionStateHistory {
  id: string;
  decisionId: string;
  type: 'creation' | 'update' | 'status_change' | 'assignment';
  changes: Record<string, unknown>;
  timestamp: string;
  userId: string;
}