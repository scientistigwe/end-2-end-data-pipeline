// src/decisions/api/decisionsApi.ts
import { baseAxiosClient, ServiceType } from '@/common/api/client/baseClient';
import type { 
  ApiResponse, 
  ApiError,
  ErrorResponse,
} from '@/common/types/api';
import {  HTTP_STATUS, ERROR_CODES } from '@/common/types/api';

import type {
  Decision,
  DecisionDetails,
  DecisionFilters,
  DecisionHistoryEntry,
  DecisionImpactAnalysis,
  DecisionState
} from '../types';

interface DecisionErrorMetadata {
  retryable: boolean;
  critical: boolean;
  code: string;
}

interface DecisionErrorMetadata {
  retryable: boolean;
  critical: boolean;
  code: string;
}

class DecisionsApi {
  private client = baseAxiosClient;
  private static readonly ERROR_METADATA: Record<number, DecisionErrorMetadata> = {
    [HTTP_STATUS.LOCKED]: {
      retryable: false,
      critical: true,
      code: 'DECISION_LOCKED'
    },
    [HTTP_STATUS.CONFLICT]: {
      retryable: true,
      critical: false,
      code: 'DECISION_CONFLICT'
    }
  };

  constructor() {
    this.client.setServiceConfig({
      service: ServiceType.DECISIONS
    });
  }

  // Core Decision Methods
  async listDecisions(pipelineId: string, filters?: DecisionFilters): Promise<ApiResponse<Decision[]>> {
    return this.client.executeGet(
      this.client.createRoute('DECISIONS', 'LIST'),
      { params: { pipeline_id: pipelineId, ...filters } }
    );
  }

  async getDecision(id: string): Promise<ApiResponse<DecisionDetails>> {
    return this.client.executeGet(
      this.client.createRoute('DECISIONS', 'GET', { decision_id: id })
    );
  }

  async createDecision(data: Omit<Decision, 'id'>): Promise<ApiResponse<Decision>> {
    return this.client.executePost(
      this.client.createRoute('DECISIONS', 'LIST'),
      data
    );
  }

  // Decision Actions
  async makeDecision(
    id: string, 
    optionId: string, 
    comment?: string
  ): Promise<ApiResponse<Decision>> {
    await this.acquireDecisionLock(id);
    try {
      return await this.client.executePost(
        this.client.createRoute('DECISIONS', 'MAKE', { decision_id: id }),
        { optionId, comment }
      );
    } finally {
      await this.releaseDecisionLock(id);
    }
  }

  async deferDecision(
    id: string, 
    reason: string, 
    deferUntil: string
  ): Promise<ApiResponse<Decision>> {
    await this.acquireDecisionLock(id);
    try {
      return await this.client.executePost(
        this.client.createRoute('DECISIONS', 'DEFER', { decision_id: id }),
        { reason, deferUntil }
      );
    } finally {
      await this.releaseDecisionLock(id);
    }
  }

  // Decision Analysis
  async getDecisionHistory(pipelineId: string): Promise<ApiResponse<DecisionHistoryEntry[]>> {
    return this.client.executeGet(
      this.client.createRoute('DECISIONS', 'HISTORY', { pipeline_id: pipelineId })
    );
  }

  async analyzeImpact(
    id: string, 
    optionId: string
  ): Promise<ApiResponse<DecisionImpactAnalysis>> {
    return this.client.executeGet(
      this.client.createRoute('DECISIONS', 'IMPACT', { 
        decision_id: id,
        option_id: optionId 
      })
    );
  }

  async getDecisionState(id: string): Promise<ApiResponse<DecisionState>> {
    return this.client.executeGet(
      this.client.createRoute('DECISIONS', 'STATE', { decision_id: id })
    );
  }

  // Lock Management
  private async acquireDecisionLock(id: string): Promise<ApiResponse<void>> {
    try {
      return await this.client.executePost(
        this.client.createRoute('DECISIONS', 'LOCK', { decision_id: id })
      );
    } catch (error) {
      throw this.handleDecisionError(error);
    }
  }

  private async releaseDecisionLock(id: string): Promise<void> {
    try {
      await this.client.executeDelete(
        this.client.createRoute('DECISIONS', 'LOCK', { decision_id: id })
      );
    } catch (error) {
      console.error('Failed to release decision lock:', error);
    }
  }

  // Decision Updates
  async updateDecision(
    id: string, 
    updates: Partial<Omit<Decision, 'id' | 'createdAt' | 'createdBy'>>
  ): Promise<ApiResponse<Decision>> {
    await this.acquireDecisionLock(id);
    try {
      return await this.client.executePut(
        this.client.createRoute('DECISIONS', 'UPDATE', { decision_id: id }),
        updates
      );
    } finally {
      await this.releaseDecisionLock(id);
    }
  }

  async deleteDecision(id: string): Promise<ApiResponse<void>> {
    return this.client.executeDelete(
      this.client.createRoute('DECISIONS', 'GET', { decision_id: id })
    );
  }

  async addComment(id: string, comment: string): Promise<ApiResponse<void>> {
    return this.client.executePost(
      this.client.createRoute('DECISIONS', 'COMMENT', { decision_id: id }),
      { comment }
    );
  }

  // Error Handling
  private isErrorResponse(error: unknown): error is ErrorResponse {
    return (
      typeof error === 'object' &&
      error !== null &&
      'error' in error &&
      typeof (error as ErrorResponse).error === 'object'
    );
  }

  private handleDecisionError(error: unknown): ApiError {
    if (this.isErrorResponse(error)) {
      const errorMetadata = DecisionsApi.ERROR_METADATA[error.error.status];
      if (errorMetadata) {
        return {
          code: errorMetadata.code,
          message: error.error.message || this.getDefaultErrorMessage(errorMetadata.code),
          status: error.error.status,
          details: error.error.details
        };
      }
      return {
        code: error.error.code,
        message: error.error.message,
        status: error.error.status,
        details: error.error.details
      };
    }
    return {
      code: ERROR_CODES.UNKNOWN_ERROR,
      message: error instanceof Error ? error.message : 'An unknown error occurred',
      status: HTTP_STATUS.INTERNAL_SERVER_ERROR
    };
  }

  private getDefaultErrorMessage(code: string): string {
    switch (code) {
      case 'DECISION_LOCKED':
        return 'Decision is locked by another user';
      case 'DECISION_CONFLICT':
        return 'Decision has been modified by another user';
      default:
        return 'An error occurred while processing the decision';
    }
  }
}

export const decisionsApi = new DecisionsApi();