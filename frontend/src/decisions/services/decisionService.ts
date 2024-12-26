// src/decisions/services/decisionService.ts
import { decisionsApi } from '../api/decisionsApi';
import { handleApiError } from '../../common/utils/api/apiUtils';
import { dateUtils } from '../../common/utils/date/dateUtils';
import type {
  Decision,
  DecisionDetails,
  DecisionFilters,
  DecisionVote,
  DecisionComment,
  DecisionHistoryEntry,
  DecisionImpactAnalysis
} from '../types/base';

export class DecisionService {
  static async listDecisions(pipelineId: string, filters?: DecisionFilters): Promise<Decision[]> {
    try {
      const response = await decisionsApi.listDecisions(pipelineId, filters);
      return response.data.map(DecisionService.transformDecision);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  static async getDecisionDetails(decisionId: string): Promise<DecisionDetails> {
    try {
      const response = await decisionsApi.getDecisionDetails(decisionId);
      return DecisionService.transformDecisionDetails(response.data);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  static async makeDecision(
    decisionId: string,
    optionId: string,
    comment?: string
  ): Promise<Decision> {
    try {
      const response = await decisionsApi.makeDecision(decisionId, optionId, comment);
      return DecisionService.transformDecision(response.data);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  static async deferDecision(
    decisionId: string,
    reason: string,
    deferUntil: string
  ): Promise<Decision> {
    try {
      const response = await decisionsApi.deferDecision(decisionId, reason, deferUntil);
      return DecisionService.transformDecision(response.data);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  static async addVote(
    decisionId: string,
    vote: DecisionVote,
    comment?: string
  ): Promise<DecisionHistoryEntry> {
    try {
      const response = await decisionsApi.addVote(decisionId, vote, comment);
      return DecisionService.transformHistoryEntry(response.data);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  static async addComment(
    decisionId: string,
    content: string,
    replyTo?: string
  ): Promise<DecisionComment> {
    try {
      const response = await decisionsApi.addComment(decisionId, content, replyTo);
      return DecisionService.transformComment(response.data);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  static async getDecisionHistory(decisionId: string): Promise<DecisionHistoryEntry[]> {
    try {
      const response = await decisionsApi.getDecisionHistory(decisionId);
      return response.data.map(DecisionService.transformHistoryEntry);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  static async analyzeImpact(
    decisionId: string,
    optionId: string
  ): Promise<DecisionImpactAnalysis> {
    try {
      const response = await decisionsApi.analyzeImpact(decisionId, optionId);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  private static transformDecision(decision: Decision): Decision {
    return {
      ...decision,
      createdAt: dateUtils.formatDate(decision.createdAt),
      updatedAt: dateUtils.formatDate(decision.updatedAt),
      deadline: decision.deadline ? dateUtils.formatDate(decision.deadline) : undefined
    };
  }

  private static transformDecisionDetails(details: DecisionDetails): DecisionDetails {
    return {
      ...DecisionService.transformDecision(details),
      history: details.history?.map(DecisionService.transformHistoryEntry) || [],
      comments: details.comments?.map(DecisionService.transformComment) || []
    };
  }

  private static transformHistoryEntry(entry: DecisionHistoryEntry): DecisionHistoryEntry {
    return {
      ...entry,
      timestamp: dateUtils.formatDate(entry.timestamp)
    };
  }

  private static transformComment(comment: DecisionComment): DecisionComment {
    return {
      ...comment,
      timestamp: dateUtils.formatDate(comment.timestamp)
    };
  }
}