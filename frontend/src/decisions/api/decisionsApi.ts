import { baseAxiosClient } from '@/common/api/client/baseClient';
import type { ApiResponse } from '@/common/types/api';
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

class DecisionsApi {
  private client = baseAxiosClient;

  constructor() {
    this.setupDecisionHeaders();
    this.setupDecisionInterceptors();
  }

  private setupDecisionHeaders() {
    this.client.setDefaultHeaders({
      'X-Service': 'decisions'
    });
  }

  // Interceptors and Error Handling
  private setupDecisionInterceptors() {
    // Add custom interceptor on the axios instance
    const instance = (this.client as any).client;
    if (!instance) return;

    instance.interceptors.request.use(
      (config) => {
        config.headers.set('X-Decision-Context', localStorage.getItem('decisionContext'));
        return config;
      },
      (error) => Promise.reject(error)
    );

    instance.interceptors.response.use(
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
    return this.client.executeGet<Decision[]>(
      this.client.createRoute('DECISIONS', 'LIST'),
      { params: { pipelineId, ...filters } }
    );
  }

  async getDecisionDetails(id: string) {
    return this.client.executeGet<DecisionDetails>(
      this.client.createRoute('DECISIONS', 'DETAILS', { id })
    );
  }

  async makeDecision(id: string, optionId: string, comment?: string) {
    await this.acquireDecisionLock(id);
    try {
      return await this.client.executePost<Decision>(
        this.client.createRoute('DECISIONS', 'MAKE', { id }),
        { optionId, comment }
      );
    } finally {
      await this.releaseDecisionLock(id);
    }
  }

  async deferDecision(id: string, reason: string, deferUntil: string) {
    await this.acquireDecisionLock(id);
    try {
      return await this.client.executePost<Decision>(
        this.client.createRoute('DECISIONS', 'DEFER', { id }),
        { reason, deferUntil }
      );
    } finally {
      await this.releaseDecisionLock(id);
    }
  }

  // Pipeline History Methods
  async getDecisionHistory(pipelineId: string) {
    return this.client.executeGet<DecisionHistoryEntry[]>(
      this.client.createRoute('DECISIONS', 'HISTORY', { id: pipelineId })
    );
  }

  // Analysis Methods
  async analyzeImpact(id: string, optionId: string) {
    return this.client.executeGet<DecisionImpactAnalysis>(
      this.client.createRoute('DECISIONS', 'ANALYZE_IMPACT', { id, optionId })
    );
  }

  // Lock Management
  private async acquireDecisionLock(id: string) {
    try {
      await this.client.executePost(
        this.client.createRoute('DECISIONS', 'LOCK', { id })
      );
    } catch (error) {
      throw this.handleDecisionError(error);
    }
  }

  private async releaseDecisionLock(id: string) {
    try {
      await this.client.executeDelete(
        this.client.createRoute('DECISIONS', 'LOCK', { id })
      );
    } catch (error) {
      console.error('Failed to release decision lock:', error);
    }
  }

  // State Management
  private async validateDecisionState(id: string): Promise<DecisionState> {
    try {
      return (await this.client.executeGet<DecisionState>(
        this.client.createRoute('DECISIONS', 'STATE', { id })
      )).data;
    } catch (error) {
      throw this.handleDecisionError(error);
    }
  }

  // Helper Methods
  async getPipelineDecisions(pipelineId: string) {
    return this.client.executeGet<Decision[]>(
      this.client.createRoute('DECISIONS', 'LIST'),
      { params: { pipelineId } }
    );
  }

  async updateDecision(id: string, updates: Partial<Decision>) {
    await this.acquireDecisionLock(id);
    try {
      return await this.client.executePut<Decision>(
        this.client.createRoute('DECISIONS', 'DETAILS', { id }),
        updates
      );
    } finally {
      await this.releaseDecisionLock(id);
    }
  }
}

export const decisionsApi = new DecisionsApi();