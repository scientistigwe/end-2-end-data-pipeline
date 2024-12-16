// src/decisions/api/decisionsApi.ts
import { BaseClient } from '@/common/api/client/baseClient';
import { API_CONFIG } from '@/common/api/client/config';
import type { ApiRequestConfig, ApiResponse } from '@/common/types/api';
import type {
  Decision,
  DecisionDetails,
  DecisionFilters,
  DecisionVote,
  DecisionComment,
  DecisionHistoryEntry,
  DecisionImpactAnalysis,
  DecisionState
} from '../types/decisions';

class DecisionsApi extends BaseClient {
  constructor() {
    super({
      baseURL: import.meta.env.VITE_DECISIONS_API_URL || API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        ...API_CONFIG.DEFAULT_HEADERS,
        'X-Service': 'decisions'
      }
    });

    this.setupDecisionInterceptors();
  }

  // Interceptors and Error Handling
  private setupDecisionInterceptors() {
    this.client.interceptors.request.use(
      (config) => {
        config.headers.set('X-Decision-Context', localStorage.getItem('decisionContext'));
        config.headers.set('X-Decision-Timestamp', new Date().toISOString());
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => {
        if (response.config.url?.includes('/decisions/')) {
          this.logDecisionEvent(response);
        }
        return response;
      },
      (error) => {
        if (error.response?.status === 409) {
          this.handleDecisionConflict(error);
        }
        throw this.handleDecisionError(error);
      }
    );
  }

  private logDecisionEvent(response: any) {
    console.log('Decision Event:', {
      url: response.config.url,
      method: response.config.method,
      status: response.status,
      timestamp: new Date().toISOString()
    });
  }

  private handleDecisionConflict(error: any) {
    console.error('Decision Conflict:', {
      url: error.config.url,
      method: error.config.method,
      conflictReason: error.response?.data?.reason
    });
  }

  private handleDecisionError(error: any): Error {
    if (error.response?.status === 423) {
      return new Error('Decision is locked by another user');
    }
    if (error.response?.status === 409) {
      return new Error('Decision has been modified by another user');
    }
    return error;
  }

  // Core Decision Methods
  async listDecisions(pipelineId: string, filters?: DecisionFilters) {
    return this.get<Decision[]>(
      API_CONFIG.ENDPOINTS.DECISIONS.LIST,
      {
        params: { pipelineId, ...filters }
      }
    );
  }

  async getDecisionDetails(id: string) {
    return this.get<DecisionDetails>(
      API_CONFIG.ENDPOINTS.DECISIONS.DETAILS,
      {
        routeParams: { id }
      }
    );
  }

  async makeDecision(id: string, optionId: string, comment?: string) {
    await this.acquireDecisionLock(id);
    try {
      return await this.post<Decision>(
        API_CONFIG.ENDPOINTS.DECISIONS.MAKE,
        { optionId, comment },
        { routeParams: { id } }
      );
    } finally {
      await this.releaseDecisionLock(id);
    }
  }

  async deferDecision(id: string, reason: string, deferUntil: string) {
    await this.acquireDecisionLock(id);
    try {
      return await this.post<Decision>(
        API_CONFIG.ENDPOINTS.DECISIONS.DEFER,
        { reason, deferUntil },
        { routeParams: { id } }
      );
    } finally {
      await this.releaseDecisionLock(id);
    }
  }

  // Voting and Comments
  async addVote(id: string, vote: DecisionVote, comment?: string) {
    return this.post<DecisionHistoryEntry>(
      API_CONFIG.ENDPOINTS.DECISIONS.VOTE,
      { vote, comment },
      { routeParams: { id } }
    );
  }

  async addComment(id: string, content: string, replyTo?: string) {
    return this.post<DecisionComment>(
      API_CONFIG.ENDPOINTS.DECISIONS.COMMENT,
      { content, replyTo },
      { routeParams: { id } }
    );
  }

  async getDecisionHistory(id: string) {
    return this.get<DecisionHistoryEntry[]>(
      API_CONFIG.ENDPOINTS.DECISIONS.HISTORY,
      { routeParams: { id } }
    );
  }

  // Analysis Methods
  async analyzeImpact(id: string, optionId: string) {
    return this.get<DecisionImpactAnalysis>(
      API_CONFIG.ENDPOINTS.DECISIONS.ANALYZE,
      {
        routeParams: { id },
        params: { optionId }
      }
    );
  }

  // Lock Management
  private async acquireDecisionLock(id: string) {
    try {
      await this.post(`/decisions/${id}/lock`);
    } catch (error) {
      throw this.handleDecisionError(error);
    }
  }

  private async releaseDecisionLock(id: string) {
    try {
      await this.delete(`/decisions/${id}/lock`);
    } catch (error) {
      console.error('Failed to release decision lock:', error);
    }
  }

  // State Management
  private async validateDecisionState(id: string): Promise<DecisionState> {
    try {
      const response = await this.get<DecisionState>(`/decisions/${id}/state`);
      return response.data;
    } catch (error) {
      throw this.handleDecisionError(error);
    }
  }

  // Helper Methods
  async getPipelineDecisions(pipelineId: string) {
    return this.get<Decision[]>(
      API_CONFIG.ENDPOINTS.DECISIONS.LIST,
      { params: { pipelineId } }
    );
  }

  async getDecisionVotes(id: string) {
    return this.get<DecisionVote[]>(
      API_CONFIG.ENDPOINTS.DECISIONS.VOTE,
      { routeParams: { id } }
    );
  }

  async getDecisionComments(id: string) {
    return this.get<DecisionComment[]>(
      API_CONFIG.ENDPOINTS.DECISIONS.COMMENT,
      { routeParams: { id } }
    );
  }

  async updateDecision(id: string, updates: Partial<Decision>) {
    await this.acquireDecisionLock(id);
    try {
      return await this.put<Decision>(
        API_CONFIG.ENDPOINTS.DECISIONS.DETAILS,
        updates,
        { routeParams: { id } }
      );
    } finally {
      await this.releaseDecisionLock(id);
    }
  }
}

export const decisionsApi = new DecisionsApi();