// src/decisions/constants.ts
import { DecisionType, DecisionStatus, DecisionUrgency } from './types/decisions';

export const DECISION_TYPES: DecisionType[] = [
  'quality',
  'pipeline',
  'security'
];

export const DECISION_STATUSES: DecisionStatus[] = [
  'pending',
  'completed',
  'deferred',
  'expired'
];

export const DECISION_URGENCIES: DecisionUrgency[] = [
  'high',
  'medium',
  'low'
];

export const DECISION_CONFIG = {
  EXPIRY_WARNING_HOURS: 24,
  DEFAULT_REFRESH_INTERVAL: 60000, // 1 minute
  MAX_COMMENT_LENGTH: 1000,
  MIN_REASON_LENGTH: 10,
  MAX_OPTIONS: 5,
  TIMELINE_POLL_INTERVAL: 30000, // 30 seconds
} as const;

export const DECISION_MESSAGES = {
  ERRORS: {
    LOAD_FAILED: 'Failed to load decisions',
    MAKE_FAILED: 'Failed to make decision',
    DEFER_FAILED: 'Failed to defer decision',
    VOTE_FAILED: 'Failed to record vote',
    INVALID_OPTION: 'Invalid decision option selected',
    EXPIRED: 'This decision has expired',
    INSUFFICIENT_PERMISSIONS: 'You do not have permission to perform this action',
  },
  SUCCESS: {
    DECISION_MADE: 'Decision recorded successfully',
    DECISION_DEFERRED: 'Decision deferred successfully',
    VOTE_RECORDED: 'Vote recorded successfully',
  },
  WARNINGS: {
    EXPIRING_SOON: 'This decision requires immediate attention!',
    NO_DECISIONS: 'No decisions found',
    INCOMPLETE_DATA: 'Some decision data may be incomplete',
  },
} as const;

export const DECISION_ENDPOINTS = {
  LIST: '/api/decisions',
  DETAILS: '/api/decisions/:id',
  MAKE: '/api/decisions/:id/make',
  DEFER: '/api/decisions/:id/defer',
  VOTE: '/api/decisions/:id/votes',
  COMMENTS: '/api/decisions/:id/comments',
  HISTORY: '/api/decisions/:id/history',
  IMPACT: '/api/decisions/:id/impact',
} as const;