// src/decisions/types/filters.ts
import type { DecisionType, DecisionStatus, DecisionUrgency } from './base';

export interface DateRange {
  start?: string;
  end?: string;
}

export interface DecisionFilters {
  types?: DecisionType[];
  status?: DecisionStatus[];
  urgency?: DecisionUrgency[];
  assignedTo?: string[];
  dateRange?: DateRange;
}