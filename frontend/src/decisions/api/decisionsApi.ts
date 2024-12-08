// src/decisions/api/decisionsApi.ts
import { decisionsClient } from './client';
import { API_CONFIG } from './config';
import type { ApiResponse } from '../../common/types/api';
import type {
  Decision,
  DecisionDetails,
  DecisionFilters,
  DecisionVote,
  DecisionComment,
  DecisionHistoryEntry,
  DecisionImpactAnalysis
} from '../types/decisions';

export class DecisionsApi {
  async listDecisions(pipelineId: string, filters?: DecisionFilters): Promise<ApiResponse<Decision[]>> {
    return decisionsClient.request('get', API_CONFIG.ENDPOINTS.DECISIONS.LIST, {
      params: { pipelineId, ...filters }
    });
  }

  async getDecisionDetails(id: string): Promise<ApiResponse<DecisionDetails>> {
    return decisionsClient.request('get', API_CONFIG.ENDPOINTS.DECISIONS.DETAILS.replace(':id', id));
  }

  async makeDecision(id: string, optionId: string, comment?: string): Promise<ApiResponse<Decision>> {
    return decisionsClient.request(
      'post', 
      API_CONFIG.ENDPOINTS.DECISIONS.MAKE.replace(':id', id),
      {},
      { optionId, comment }
    );
  }

  async deferDecision(id: string, reason: string, deferUntil: string): Promise<ApiResponse<Decision>> {
    return decisionsClient.request(
      'post',
      API_CONFIG.ENDPOINTS.DECISIONS.DEFER.replace(':id', id),
      {},
      { reason, deferUntil }
    );
  }

  async addVote(id: string, vote: DecisionVote, comment?: string): Promise<ApiResponse<DecisionHistoryEntry>> {
    return decisionsClient.request(
      'post',
      API_CONFIG.ENDPOINTS.DECISIONS.VOTE.replace(':id', id),
      {},
      { vote, comment }
    );
  }

  async addComment(id: string, content: string, replyTo?: string): Promise<ApiResponse<DecisionComment>> {
    return decisionsClient.request(
      'post',
      API_CONFIG.ENDPOINTS.DECISIONS.COMMENT.replace(':id', id),
      {},
      { content, replyTo }
    );
  }

  async getDecisionHistory(id: string): Promise<ApiResponse<DecisionHistoryEntry[]>> {
    return decisionsClient.request('get', API_CONFIG.ENDPOINTS.DECISIONS.HISTORY.replace(':id', id));
  }

  async analyzeImpact(id: string, optionId: string): Promise<ApiResponse<DecisionImpactAnalysis>> {
    return decisionsClient.request('get', API_CONFIG.ENDPOINTS.DECISIONS.ANALYZE.replace(':id', id), {
      params: { optionId }
    });
  }
}

export const decisionsApi = new DecisionsApi();