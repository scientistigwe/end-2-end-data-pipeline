import { baseAxiosClient } from '@/common/api/client/baseClient';
import type { ApiResponse } from '@/common/types/api';
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
} from '../types/recommendations';
import { RECOMMENDATION_EVENTS } from '../types/recommendations';

class RecommendationsApi {
  private client = baseAxiosClient;
  private readonly RECOMMENDATION_EVENTS = RECOMMENDATION_EVENTS;

  constructor() {
    this.setupRecommendationHeaders();
    this.setupRecommendationInterceptors();
  }

  private setupRecommendationHeaders() {
    this.client.setDefaultHeaders({
      'X-Service': 'recommendations'
    });
  }

  // Interceptors and Error Handling
  private setupRecommendationInterceptors() {
    // Add custom interceptor on the axios instance
    const instance = (this.client as any).client;
    if (!instance) return;

    instance.interceptors.request.use(
      (config) => {
        return config;
      }
    );

    instance.interceptors.response.use(
      response => {
        this.handleRecommendationEvents(response);
        return response;
      },
      error => {
        const enhancedError = this.handleRecommendationError(error);
        this.notifyError(enhancedError);
        throw enhancedError;
      }
    );
  }

  private handleRecommendationError(error: unknown): RecommendationError {
    const baseError: RecommendationError = {
      name: 'RecommendationError',
      message: 'Unknown recommendation error',
      timestamp: new Date().toISOString(),
      component: 'recommendation'
    };

    if (error instanceof Error) {
      return {
        ...error,
        ...baseError,
        message: error.message
      };
    }

    if (typeof error === 'object' && error !== null) {
      const errorObj = error as Record<string, any>;
      if (errorObj.response?.status === 409) {
        return {
          ...baseError,
          message: 'Recommendation has already been applied or dismissed',
          code: 'ALREADY_HANDLED'
        };
      }
      if (errorObj.response?.status === 404) {
        return {
          ...baseError,
          message: 'Recommendation not found',
          code: 'NOT_FOUND'
        };
      }
    }

    return baseError;
  }

  private handleRecommendationEvents(response: any) {
    const url = response.config.url;
    if (url?.includes('/apply')) {
      this.notifyApplied(response.data.recommendationId, response.data.actionId, response.data);
    } else if (url?.includes('/dismiss')) {
      this.notifyDismissed(response.data.recommendationId, response.data.reason);
    }
  }

  // Event Notification Methods
  private notifyError(error: RecommendationError): void {
    window.dispatchEvent(
      new CustomEvent<RecommendationErrorDetail>(this.RECOMMENDATION_EVENTS.ERROR, {
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
      new CustomEvent<RecommendationAppliedDetail>(this.RECOMMENDATION_EVENTS.APPLIED, {
        detail: { recommendationId, actionId, result }
      })
    );
  }

  private notifyDismissed(recommendationId: string, reason?: string): void {
    window.dispatchEvent(
      new CustomEvent<RecommendationDismissedDetail>(this.RECOMMENDATION_EVENTS.DISMISSED, {
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
        this.RECOMMENDATION_EVENTS.STATUS_CHANGE,
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
      this.client.createRoute('RECOMMENDATIONS', 'LIST'),
      { 
        routeParams: { id: pipelineId },
        params: filters 
      }
    );
  }

  async getRecommendationDetails(
    recommendationId: string
  ): Promise<ApiResponse<Recommendation>> {
    return this.client.executeGet(
      this.client.createRoute('RECOMMENDATIONS', 'DETAILS', { id: recommendationId })
    );
  }

  async applyRecommendation(
    recommendationId: string,
    actionId: string,
    parameters?: Record<string, unknown>
  ): Promise<ApiResponse<RecommendationHistory>> {
    return this.client.executePost(
      this.client.createRoute('RECOMMENDATIONS', 'APPLY', { id: recommendationId }),
      { actionId, parameters }
    );
  }

  async dismissRecommendation(
    recommendationId: string,
    reason?: string
  ): Promise<ApiResponse<void>> {
    return this.client.executePost(
      this.client.createRoute('RECOMMENDATIONS', 'DISMISS', { id: recommendationId }),
      { reason }
    );
  }

  async getApplicationStatus(
    recommendationId: string
  ): Promise<ApiResponse<RecommendationHistory>> {
    return this.client.executeGet(
      this.client.createRoute('RECOMMENDATIONS', 'STATUS', { id: recommendationId })
    );
  }

  async getRecommendationHistory(
    pipelineId: string
  ): Promise<ApiResponse<RecommendationHistory[]>> {
    return this.client.executeGet(
      this.client.createRoute('RECOMMENDATIONS', 'HISTORY', { id: pipelineId })
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
  subscribeToEvents<E extends RecommendationEventName>(
    event: E,
    callback: (event: RecommendationEventMap[E]) => void
  ): () => void {
    const handler = (e: Event) => callback(e as RecommendationEventMap[E]);
    window.addEventListener(event, handler);
    return () => window.removeEventListener(event, handler);
  }
}

// Export singleton instance
export const recommendationsApi = new RecommendationsApi();