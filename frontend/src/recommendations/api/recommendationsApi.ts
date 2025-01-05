// src/recommendations/api/recommendationsApi.ts
import { RouteHelper } from '@/common/api/routes';
import { baseAxiosClient, ServiceType } from '@/common/api/client/baseClient';
import { 
  ApiResponse, 
  HTTP_STATUS,
  ERROR_CODES 
} from '@/common/types/api';
import type { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import type {
  Recommendation,
  RecommendationHistory,
  RecommendationFilters,
  RecommendationError,
  RecommendationEventMap,
  RecommendationEventName,
  RecommendationAppliedDetail,
  RecommendationDismissedDetail,
  RecommendationStatusChangeDetail,
  RecommendationErrorDetail
} from '../types';
import { RECOMMENDATION_EVENTS } from '../types';

interface RecommendationErrorMetadata {
  retryable: boolean;
  critical: boolean;
  code: string;
}

class RecommendationsApi {
  private client = baseAxiosClient;
  private static readonly ERROR_METADATA: Record<number, RecommendationErrorMetadata> = {
    [HTTP_STATUS.CONFLICT]: {
      retryable: false,
      critical: false,
      code: 'ALREADY_HANDLED'
    },
    [HTTP_STATUS.NOT_FOUND]: {
      retryable: false,
      critical: true,
      code: 'NOT_FOUND'
    }
  };

  constructor() {
    this.client.setServiceConfig({
      service: ServiceType.RECOMMENDATIONS,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      }
    });
    this.setupRecommendationInterceptors();  // Keep your existing interceptors
  }

  private setupRecommendationInterceptors(): void {
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

  private handleRequestInterceptor = (
    config: InternalAxiosRequestConfig
  ): InternalAxiosRequestConfig | Promise<InternalAxiosRequestConfig> => {
    return config;
  };

  private handleRequestError = (error: unknown): Promise<never> => {
    return Promise.reject(this.handleRecommendationError(error));
  };

  private handleResponseInterceptor = (
    response: AxiosResponse
  ): AxiosResponse | Promise<AxiosResponse> => {
    this.handleRecommendationEvents(response);
    return response;
  };

  private handleResponseError = (error: unknown): Promise<never> => {
    const enhancedError = this.handleRecommendationError(error);
    this.notifyError(enhancedError);
    throw enhancedError;
  };

  private handleRecommendationError(error: unknown): RecommendationError {
    const baseError: RecommendationError = {
      name: 'RecommendationError',
      message: 'Unknown recommendation error',
      timestamp: new Date().toISOString(),
      component: 'recommendation'
    };

    if (error instanceof Error) {
      return {
        ...baseError,
        message: error.message,
        stack: error.stack
      };
    }

    if (typeof error === 'object' && error !== null) {
      const errorObj = error as Record<string, any>;
      const status = errorObj.response?.status;
      const errorMetadata = RecommendationsApi.ERROR_METADATA[status];

      if (errorMetadata) {
        return {
          ...baseError,
          code: errorMetadata.code,
          message: this.getErrorMessage(errorMetadata.code)
        };
      }
    }

    return baseError;
  }

  private getErrorMessage(code: string): string {
    switch (code) {
      case 'ALREADY_HANDLED':
        return 'Recommendation has already been applied or dismissed';
      case 'NOT_FOUND':
        return 'Recommendation not found';
      default:
        return 'An error occurred processing the recommendation';
    }
  }

  private handleRecommendationEvents(response: AxiosResponse): void {
    const url = response.config.url;
    if (!url) return;

    if (url.includes('/apply')) {
      this.notifyApplied(
        response.data.recommendationId, 
        response.data.actionId, 
        response.data
      );
    } else if (url.includes('/dismiss')) {
      this.notifyDismissed(
        response.data.recommendationId, 
        response.data.reason
      );
    }
  }

  // Event Notification Methods
  private notifyError(error: RecommendationError): void {
    window.dispatchEvent(
      new CustomEvent<RecommendationErrorDetail>(RECOMMENDATION_EVENTS.ERROR, {
        detail: {
          error: error.message,
          code: error.code
        }
      })
    );
  }

  private notifyApplied(
    recommendationId: string,
    actionId: string,
    result: RecommendationHistory
  ): void {
    window.dispatchEvent(
      new CustomEvent<RecommendationAppliedDetail>(RECOMMENDATION_EVENTS.APPLIED, {
        detail: { recommendationId, actionId, result }
      })
    );
  }

  private notifyDismissed(recommendationId: string, reason?: string): void {
    window.dispatchEvent(
      new CustomEvent<RecommendationDismissedDetail>(RECOMMENDATION_EVENTS.DISMISSED, {
        detail: { recommendationId, reason }
      })
    );
  }

  private notifyStatusChange(
    recommendationId: string,
    status: string,
    previousStatus?: string
  ): void {
    window.dispatchEvent(
      new CustomEvent<RecommendationStatusChangeDetail>(
        RECOMMENDATION_EVENTS.STATUS_CHANGE,
        {
          detail: { recommendationId, status, previousStatus }
        }
      )
    );
  }

  // Core Recommendation Methods
  async getRecommendations(
    pipelineId: string,
    filters?: RecommendationFilters
  ): Promise<ApiResponse<Recommendation[]>> {
    return this.client.executeGet(
      RouteHelper.getRoute('RECOMMENDATIONS', 'LIST'),
      { params: { pipeline_id: pipelineId, ...filters } }
    );
  }

  async getRecommendationDetails(
    recommendationId: string
  ): Promise<ApiResponse<Recommendation>> {
    return this.client.executeGet(
      RouteHelper.getRoute('RECOMMENDATIONS', 'GET', { recommendation_id: recommendationId })
    );
  }

  async applyRecommendation(
    recommendationId: string,
    actionId: string,
    parameters?: Record<string, unknown>
  ): Promise<ApiResponse<RecommendationHistory>> {
    return this.client.executePost(
      RouteHelper.getRoute('RECOMMENDATIONS', 'APPLY', { recommendation_id: recommendationId }),
      { actionId, parameters }
    );
  }

  async dismissRecommendation(
    recommendationId: string,
    reason?: string
  ): Promise<ApiResponse<void>> {
    return this.client.executePost(
      RouteHelper.getRoute('RECOMMENDATIONS', 'DISMISS', { recommendation_id: recommendationId }),
      { reason }
    );
  }

  async getApplicationStatus(
    recommendationId: string
  ): Promise<ApiResponse<RecommendationHistory>> {
    return this.client.executeGet(
      RouteHelper.getRoute('RECOMMENDATIONS', 'STATUS', { recommendation_id: recommendationId })
    );
  }

  async getRecommendationHistory(
    pipelineId: string
  ): Promise<ApiResponse<RecommendationHistory[]>> {
    return this.client.executeGet(
      RouteHelper.getRoute('RECOMMENDATIONS', 'HISTORY', { pipeline_id: pipelineId })
    );
  }

  // Helper Methods
  async waitForRecommendationApplication(
    recommendationId: string,
    options?: {
      pollingInterval?: number;
      timeout?: number;
    }
  ): Promise<RecommendationHistory> {
    const interval = options?.pollingInterval || 2000;
    const timeout = options?.timeout || 60000;
    const startTime = Date.now();

    const checkStatus = async (): Promise<RecommendationHistory> => {
      if (Date.now() - startTime >= timeout) {
        throw this.handleRecommendationError({
          message: 'Recommendation application timeout',
          code: 'TIMEOUT'
        });
      }

      const response = await this.getApplicationStatus(recommendationId);
      const status = response.data.status;

      if (status === 'success' || status === 'failed') {
        this.notifyStatusChange(recommendationId, status);
        return response.data;
      }

      await new Promise(resolve => setTimeout(resolve, interval));
      return checkStatus();
    };

    return checkStatus();
  }

  async batchApplyRecommendations(
    recommendations: Array<{
      id: string;
      actionId: string;
      parameters?: Record<string, unknown>;
    }>
  ): Promise<ApiResponse<RecommendationHistory>[]> {
    return Promise.all(
      recommendations.map(rec => 
        this.applyRecommendation(rec.id, rec.actionId, rec.parameters)
      )
    );
  }

  async getRecommendationSummary(pipelineId: string) {
    const [recommendations, history] = await Promise.all([
      this.getRecommendations(pipelineId),
      this.getRecommendationHistory(pipelineId)
    ]);

    return {
      pending: recommendations.data,
      applied: history.data.filter(h => h.status === 'success'),
      dismissed: history.data.filter(h => h.status === 'failed')
    };
  }

  // Event Subscription
 // Event Subscription
 subscribeToEvents<E extends keyof RecommendationEventMap>(
  event: E,
  callback: (event: RecommendationEventMap[E]) => void
): () => void {
  const handler = (e: Event) => callback(e as RecommendationEventMap[E]);
  window.addEventListener(event, handler);
  return () => window.removeEventListener(event, handler);
}
}

export const recommendationsApi = new RecommendationsApi();