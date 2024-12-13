// src/decisions/utils/decisionUtils.ts
import { dateUtils } from '../../common/utils/date/dateUtils';
import { DECISION_CONFIG, DECISION_MESSAGES } from '../constants';
import type { 
  Decision, 
  DecisionOption, 
  DecisionDetails,
  DecisionHistoryEntry 
} from '../types/decisions';

export const isExpiringSoon = (decision: Decision): boolean => {
  if (!decision.deadline) return false;
  
  const deadline = new Date(decision.deadline).getTime();
  const now = new Date().getTime();
  const hoursUntilDeadline = (deadline - now) / (1000 * 60 * 60);
  
  return hoursUntilDeadline <= DECISION_CONFIG.EXPIRY_WARNING_HOURS;
};

export const validateDecisionOption = (
  decision: Decision,
  optionId: string
): { isValid: boolean; error?: string } => {
  if (!decision.options.find(opt => opt.id === optionId)) {
    return { 
      isValid: false, 
      error: DECISION_MESSAGES.ERRORS.INVALID_OPTION 
    };
  }

  if (decision.status === 'expired') {
    return { 
      isValid: false, 
      error: DECISION_MESSAGES.ERRORS.EXPIRED 
    };
  }

  return { isValid: true };
};

export const calculateImpactScore = (option: DecisionOption): number => {
  const impactWeights = {
    high: 3,
    medium: 2,
    low: 1
  };

  return impactWeights[option.impact];
};

export const sortDecisionsByPriority = (decisions: Decision[]): Decision[] => {
  return [...decisions].sort((a, b) => {
    // Sort by urgency first
    const urgencyWeights = { high: 3, medium: 2, low: 1 };
    const urgencyDiff = urgencyWeights[b.urgency] - urgencyWeights[a.urgency];
    if (urgencyDiff !== 0) return urgencyDiff;

    // Then by deadline if exists
    if (a.deadline && b.deadline) {
      return new Date(a.deadline).getTime() - new Date(b.deadline).getTime();
    }
    if (a.deadline) return -1;
    if (b.deadline) return 1;

    // Finally by creation date
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
  });
};

export const formatDecisionHistory = (history: DecisionHistoryEntry[]): DecisionHistoryEntry[] => {
  return history.map(entry => ({
    ...entry,
    timestamp: dateUtils.formatDate(entry.timestamp),
    changes: entry.changes?.map(change => ({
      ...change,
      oldValue: formatHistoryValue(change.oldValue),
      newValue: formatHistoryValue(change.newValue)
    }))
  }));
};

const formatHistoryValue = (value: unknown): string => {
  if (value === null || value === undefined) return 'None';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};

export const analyzeDecisionImpact = (details: DecisionDetails): {
  totalRisks: number;
  highImpactRisks: number;
  benefitsScore: number;
  recommendedAction: string;
} => {
  const analysis = details.analysis;
  if (!analysis) {
    return {
      totalRisks: 0,
      highImpactRisks: 0,
      benefitsScore: 0,
      recommendedAction: 'Insufficient data for analysis'
    };
  }

  const totalRisks = analysis.risks.length;
  const highImpactRisks = analysis.risks.filter(risk => risk === 'high').length;
  const benefitsScore = analysis.benefits.length;

  let recommendedAction = 'Proceed with caution';
  if (highImpactRisks > totalRisks / 2) {
    recommendedAction = 'Consider alternatives';
  } else if (benefitsScore > totalRisks * 2) {
    recommendedAction = 'Proceed with implementation';
  }

  return {
    totalRisks,
    highImpactRisks,
    benefitsScore,
    recommendedAction
  };
};

export const generateDecisionSummary = (decision: DecisionDetails): string => {
  const impact = analyzeDecisionImpact(decision);
  const deadline = decision.deadline ? 
    `Deadline: ${dateUtils.formatDate(decision.deadline)}` : 
    'No deadline set';

  return `
    ${decision.title} (${decision.type})
    Status: ${decision.status}
    ${deadline}
    Options: ${decision.options.length}
    Risks: ${impact.totalRisks} (${impact.highImpactRisks} high impact)
    Benefits Score: ${impact.benefitsScore}
    Recommended Action: ${impact.recommendedAction}
  `.trim();
};