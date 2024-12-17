// src/decisions/api/decisionsApi.ts
import { BaseClient } from '@/common/api/client/baseClient';
import { API_CONFIG } from '@/common/api/client/config';
import { RouteHelper } from '@/common/api/routes';
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
      this.getRoute('DECISIONS', 'LIST'),
      { params: { pipelineId, ...filters } }
    );
  }

  async getDecisionDetails(id: string) {
    return this.get<DecisionDetails>(
      this.getRoute('DECISIONS', 'DETAILS', { id })
    );
  }

  async makeDecision(id: string, optionId: string, comment?: string) {
    await this.acquireDecisionLock(id);
    try {
      return await this.post<Decision>(
        this.getRoute('DECISIONS', 'MAKE', { id }),
        { optionId, comment }
      );
    } finally {
      await this.releaseDecisionLock(id);
    }
  }

  async deferDecision(id: string, reason: string, deferUntil: string) {
    await this.acquireDecisionLock(id);
    try {
      return await this.post<Decision>(
        this.getRoute('DECISIONS', 'DEFER', { id }),
        { reason, deferUntil }
      );
    } finally {
      await this.releaseDecisionLock(id);
    }
  }

  // Pipeline History Methods
  async getDecisionHistory(pipelineId: string) {
    return this.get<DecisionHistoryEntry[]>(
      this.getRoute('DECISIONS', 'HISTORY', { id: pipelineId })
    );
  }

  // Analysis Methods
  async analyzeImpact(id: string, optionId: string) {
    return this.get<DecisionImpactAnalysis>(
      this.getRoute('DECISIONS', 'ANALYZE_IMPACT', { id, optionId })
    );
  }

  // Lock Management
  private async acquireDecisionLock(id: string) {
    try {
      await this.post(
        this.getRoute('DECISIONS', 'LOCK', { id })
      );
    } catch (error) {
      throw this.handleDecisionError(error);
    }
  }

  private async releaseDecisionLock(id: string) {
    try {
      await this.delete(
        this.getRoute('DECISIONS', 'LOCK', { id })
      );
    } catch (error) {
      console.error('Failed to release decision lock:', error);
    }
  }

  // State Management
  private async validateDecisionState(id: string): Promise<DecisionState> {
    try {
      return (await this.get<DecisionState>(
        this.getRoute('DECISIONS', 'STATE', { id })
      )).data;
    } catch (error) {
      throw this.handleDecisionError(error);
    }
  }

  // Helper Methods
  async getPipelineDecisions(pipelineId: string) {
    return this.get<Decision[]>(
      this.getRoute('DECISIONS', 'LIST'),
      { params: { pipelineId } }
    );
  }

  async updateDecision(id: string, updates: Partial<Decision>) {
    await this.acquireDecisionLock(id);
    try {
      return await this.put<Decision>(
        this.getRoute('DECISIONS', 'DETAILS', { id }),
        updates
      );
    } finally {
      await this.releaseDecisionLock(id);
    }
  }
}

export const decisionsApi = new DecisionsApi();