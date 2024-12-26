// src/decisions/api/decisionsApi.ts
import { RouteHelper } from '@/common/api/routes';
import { baseAxiosClient } from '@/common/api/client/baseClient';
import { 
  ApiResponse, 
  ApiError, 
  ApiErrorResponse, 
  ApiRequestConfig,
  HTTP_STATUS,
  ERROR_CODES,
  ErrorResponse 
} from '@/common/types/api';
import type { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
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
    this.setupDecisionHeaders();
    this.setupDecisionInterceptors();
  }

  private setupDecisionHeaders(): void {
    this.client.setDefaultHeaders({
      'X-Service': 'decisions'
    });
  }

  private setupDecisionInterceptors(): void {
    const instance = this.client.getAxiosInstance();
    if (!instance) return;

    instance.interceptors.request.use(
      this.handleRequestInterceptor,
      this.handleRequestError
    );

    instance.interceptors.response.use(
      this.handleResponseInterceptor,
      this.handleResponseError
    );
  }

  private handleRequestInterceptor = (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const decisionContext = localStorage.getItem('decisionContext');
    if (decisionContext) {
      config.headers.set('X-Decision-Context', decisionContext);
    }
    return config;
  };

  private handleRequestError = (error: unknown): Promise<never> => {
    return Promise.reject(this.handleDecisionError(error));
  };

  private handleResponseInterceptor = (response: AxiosResponse): AxiosResponse => {
    if (response.config.url?.includes('/decisions/')) {
      this.logDecisionEvent(response);
    }
    return response;
  };

  private handleResponseError = (error: unknown): Promise<never> => {
    if (this.isErrorResponse(error) && error.error?.status === HTTP_STATUS.CONFLICT) {
      this.handleDecisionConflict(error);
    }
    throw this.handleDecisionError(error);
  };

  private isErrorResponse(error: unknown): error is ErrorResponse {
    return (
      typeof error === 'object' &&
      error !== null &&
      'error' in error &&
      typeof (error as ErrorResponse).error === 'object'
    );
  }

  private logDecisionEvent(response: AxiosResponse): void {
    console.log('Decision Event:', {
      url: response.config.url,
      method: response.config.method,
      status: response.status,
      timestamp: new Date().toISOString()
    });
  }

  private handleDecisionConflict(error: ErrorResponse): void {
    console.error('Decision Conflict:', {
      code: error.error.code,
      message: error.error.message,
      details: error.error.details
    });
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

  // Core Decision Methods
  async listDecisions(pipelineId: string, filters?: DecisionFilters): Promise<ApiResponse<Decision[]>> {
    return this.client.executeGet(
      RouteHelper.getRoute('DECISIONS', 'LIST'),
      { params: { pipeline_id: pipelineId, ...filters } }
    );
  }

  async getDecision(id: string): Promise<ApiResponse<DecisionDetails>> {
    return this.client.executeGet(
      RouteHelper.getRoute('DECISIONS', 'GET', { decision_id: id })
    );
  }

  async createDecision(data: Omit<Decision, 'id'>): Promise<ApiResponse<Decision>> {
    return this.client.executePost(
      RouteHelper.getRoute('DECISIONS', 'LIST'),
      data
    );
  }
  async makeDecision(
    id: string, 
    optionId: string, 
    comment?: string
  ): Promise<ApiResponse<Decision>> {
    await this.acquireDecisionLock(id);
    try {
      return await this.client.executePost(
        RouteHelper.getRoute('DECISIONS', 'MAKE', { decision_id: id }),
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
        RouteHelper.getRoute('DECISIONS', 'DEFER', { decision_id: id }),
        { reason, deferUntil }
      );
    } finally {
      await this.releaseDecisionLock(id);
    }
  }

  async getDecisionHistory(pipelineId: string): Promise<ApiResponse<DecisionHistoryEntry[]>> {
    return this.client.executeGet(
      RouteHelper.getRoute('DECISIONS', 'HISTORY', { pipeline_id: pipelineId })
    );
  }

  async analyzeImpact(
    id: string, 
    optionId: string
  ): Promise<ApiResponse<DecisionImpactAnalysis>> {
    return this.client.executeGet(
      RouteHelper.getRoute('DECISIONS', 'ANALYZE_IMPACT', { 
        decision_id: id,
        option_id: optionId 
      })
    );
  }

  async getDecisionState(id: string): Promise<ApiResponse<DecisionState>> {
    return this.client.executeGet(
      RouteHelper.getRoute('DECISIONS', 'STATE', { decision_id: id })
    );
  }

  // Lock Management
  private async acquireDecisionLock(id: string): Promise<ApiResponse<void>> {
    try {
      return await this.client.executePost(
        RouteHelper.getRoute('DECISIONS', 'LOCK', { decision_id: id })
      );
    } catch (error) {
      throw this.handleDecisionError(error);
    }
  }

  private async releaseDecisionLock(id: string): Promise<void> {
    try {
      await this.client.executeDelete(
        RouteHelper.getRoute('DECISIONS', 'LOCK', { decision_id: id })
      );
    } catch (error) {
      console.error('Failed to release decision lock:', error);
    }
  }

  async updateDecision(
    id: string, 
    updates: Partial<Omit<Decision, 'id' | 'createdAt' | 'createdBy'>>
  ): Promise<ApiResponse<Decision>> {
    await this.acquireDecisionLock(id);
    try {
      return await this.client.executePut(
        RouteHelper.getRoute('DECISIONS', 'UPDATE', { decision_id: id }),
        updates
      );
    } finally {
      await this.releaseDecisionLock(id);
    }
  }

  async deleteDecision(id: string): Promise<ApiResponse<void>> {
    return this.client.executeDelete(
      RouteHelper.getRoute('DECISIONS', 'DELETE', { decision_id: id })
    );
  }
}

export const decisionsApi = new DecisionsApi();