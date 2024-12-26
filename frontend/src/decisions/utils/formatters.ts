// src/decisions/utils/formatters.ts
import { format } from 'date-fns';
import type { 
  Decision, 
  DecisionType, 
  DecisionStatus, 
  DecisionUrgency 
} from '../types/base';

export const formatDecisionType = (type: DecisionType): string => {
  const typeMap: Record<DecisionType, string> = {
    quality: 'Quality Control',
    pipeline: 'Pipeline Management',
    security: 'Security Assessment'
  };
  return typeMap[type] || type;
};

export const formatDecisionStatus = (status: DecisionStatus): string => {
  const statusMap: Record<DecisionStatus, string> = {
    pending: 'Pending Review',
    completed: 'Completed',
    deferred: 'Deferred',
    expired: 'Expired'
  };
  return statusMap[status] || status;
};

export const formatDecisionUrgency = (urgency: DecisionUrgency): string => {
  const urgencyMap: Record<DecisionUrgency, string> = {
    high: 'High Priority',
    medium: 'Medium Priority',
    low: 'Low Priority'
  };
  return urgencyMap[urgency] || urgency;
};

export const formatDecisionDate = (date: string): string => {
  return format(new Date(date), 'PPP');
};

export const formatDecisionDeadline = (decision: Decision): string => {
  if (!decision.deadline) return 'No deadline set';
  
  const deadline = new Date(decision.deadline);
  const now = new Date();
  const hoursUntil = Math.ceil((deadline.getTime() - now.getTime()) / (1000 * 60 * 60));
  
  if (hoursUntil <= 0) return 'Expired';
  if (hoursUntil <= 24) return `Due in ${hoursUntil} hours`;
  if (hoursUntil <= 48) return 'Due tomorrow';
  
  return `Due ${format(deadline, 'PPP')}`;
};

export const formatDecisionSummary = (decision: Decision): string => {
  return `${formatDecisionType(decision.type)} - ${formatDecisionStatus(decision.status)} - ${formatDecisionUrgency(decision.urgency)}`;
};

export const formatOptionImpact = (impact: string): string => {
  return impact.charAt(0).toUpperCase() + impact.slice(1) + ' Impact';
};