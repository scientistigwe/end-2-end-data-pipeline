// src/decisions/utils/validators.ts
import { DECISION_CONFIG } from '../constants';
import type { Decision, DecisionOption } from '../types/base';

export const validateDecisionData = (data: Partial<Decision>): {
  isValid: boolean;
  errors: string[];
} => {
  const errors: string[] = [];

  if (!data.title?.trim()) {
    errors.push('Title is required');
  }

  if (!data.description?.trim()) {
    errors.push('Description is required');
  }

  if (!data.type) {
    errors.push('Decision type is required');
  }

  if (!data.urgency) {
    errors.push('Urgency level is required');
  }

  if (data.deadline) {
    const deadline = new Date(data.deadline);
    if (isNaN(deadline.getTime()) || deadline < new Date()) {
      errors.push('Invalid deadline date');
    }
  }

  if (!data.options || data.options.length === 0) {
    errors.push('At least one option is required');
  } else if (data.options.length > DECISION_CONFIG.MAX_OPTIONS) {
    errors.push(`Maximum ${DECISION_CONFIG.MAX_OPTIONS} options allowed`);
  }

  return {
    isValid: errors.length === 0,
    errors
  };
};

export const validateOption = (option: Partial<DecisionOption>): {
  isValid: boolean;
  errors: string[];
} => {
  const errors: string[] = [];

  if (!option.title?.trim()) {
    errors.push('Option title is required');
  }

  if (!option.description?.trim()) {
    errors.push('Option description is required');
  }

  if (!option.impact) {
    errors.push('Impact level is required');
  }

  if (option.consequences && !Array.isArray(option.consequences)) {
    errors.push('Consequences must be an array');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
};

export const validateDeferralReason = (reason: string): {
        isValid: boolean;
        error?: string;
      } => {
        if (!reason.trim()) {
          return {
            isValid: false,
            error: 'Deferral reason is required'
          };
        }
      
        if (reason.length < DECISION_CONFIG.MIN_REASON_LENGTH) {
          return {
            isValid: false,
            error: `Reason must be at least ${DECISION_CONFIG.MIN_REASON_LENGTH} characters`
          };
        }
      
        // Add return statement for valid case
        return {
          isValid: true
        };
      };