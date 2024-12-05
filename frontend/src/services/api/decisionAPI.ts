// src/services/api/decisionsApi.ts
import { BaseApiClient } from './client';
import { API_CONFIG } from './config';
import type { ApiResponse } from '../../types/api';
import type {
  Decision,
  DecisionDetails,
  DecisionImpactAnalysis,
  DecisionHistoryEntry,
  DecisionFilters,
  DecisionVote,
  DecisionComment
} from '../../types/decision';

class DecisionsApi extends BaseApiClient {
  /**
   * List decisions for a pipeline
   */
  async listDecisions(
    pipelineId: string,
    filters?: DecisionFilters
  ): Promise<ApiResponse<Decision[]>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DECISIONS.LIST, {
      routeParams: { id: pipelineId },
      params: filters
    });
  }

  /**
   * Get decision details
   */
  async getDecisionDetails(
    decisionId: string
  ): Promise<ApiResponse<DecisionDetails>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DECISIONS.DETAILS, {
      routeParams: { id: decisionId }
    });
  }

  /**
   * Make a decision
   */
  async makeDecision(
    decisionId: string,
    optionId: string,
    comment?: string
  ): Promise<ApiResponse<Decision>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DECISIONS.MAKE, {
      routeParams: { id: decisionId }
    }, {
      optionId,
      comment
    });
  }

  /**
   * Defer a decision
   */
  async deferDecision(
    decisionId: string,
    reason: string,
    deferUntil: string
  ): Promise<ApiResponse<Decision>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DECISIONS.DEFER, {
      routeParams: { id: decisionId }
    }, {
      reason,
      deferUntil
    });
  }

  /**
   * Get decision history
   */
  async getDecisionHistory(
    pipelineId: string
  ): Promise<ApiResponse<DecisionHistoryEntry[]>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DECISIONS.HISTORY, {
      routeParams: { id: pipelineId }
    });
  }

  /**
   * Analyze impact of a decision option
   */
  async analyzeImpact(
    decisionId: string,
    optionId: string
  ): Promise<ApiResponse<DecisionImpactAnalysis>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DECISIONS.ANALYZE_IMPACT, {
      routeParams: { id: decisionId, optionId }
    });
  }

  /**
   * Add vote to a decision
   */
  async addVote(
    decisionId: string,
    vote: DecisionVote,
    comment?: string
  ): Promise<ApiResponse<DecisionHistoryEntry>> {
    return this.request('post', `${API_CONFIG.ENDPOINTS.DECISIONS.DETAILS}/votes`, {
      routeParams: { id: decisionId }
    }, {
      vote,
      comment
    });
  }

  /**
   * Add comment to a decision
   */
  async addComment(
    decisionId: string,
    content: string,
    replyTo?: string
  ): Promise<ApiResponse<DecisionComment>> {
    return this.request('post', `${API_CONFIG.ENDPOINTS.DECISIONS.DETAILS}/comments`, {
      routeParams: { id: decisionId }
    }, {
      content,
      replyTo
    });
  }
}

export const decisionsApi = new DecisionsApi();