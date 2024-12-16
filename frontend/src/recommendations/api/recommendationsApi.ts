// src/recommendations/api/recommendationsApi.ts
import { BaseClient } from '@/common/api/client/baseClient';
import { API_CONFIG } from '@/common/api/client/config';
import type { ApiResponse } from '@/common/types/api';
import type {
  Recommendation,
  RecommendationHistory,
  RecommendationFilters
} from '../types/recommendations';

class RecommendationsApi extends BaseClient {
  private readonly RECOMMENDATION_EVENTS = {
    APPLIED: 'recommendation:applied',
    DISMISSED: 'recommendation:dismissed',
    STATUS_CHANGE: 'recommendation:statusChange',
    ERROR: 'recommendation:error'
  };

  constructor() {
    super({
      baseURL: import.meta.env.VITE_RECOMMENDATIONS_API_URL || API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        ...API_CONFIG.DEFAULT_HEADERS,
        'X-Service': 'recommendations'
      }
    });

    this.setupRecommendationInterceptors();
  }

  // Interceptors and Error Handling
  private setupRecommendationInterceptors() {
    this.client.interceptors.request.use(
      (config) => {
        config.headers.set('X-Recommendation-Timestamp', new Date().toISOString());
        return config;
      }
    );

    this.client.interceptors.response.use(
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

  private handleRecommendationError(error: any): Error {
    if (error.response?.status === 409) {
      return new Error('Recommendation has already been applied or dismissed');
    }
    if (error.response?.status === 404) {
      return new Error('Recommendation not found');
    }
    if (error.response?.status === 400) {
      return new Error(`Invalid recommendation action: ${error.response.data?.message}`);
    }
    return error;
  }

  private handleRecommendationEvents(response: any) {
    const url = response.config.url;
    if (url?.includes('/apply')) {
      this.dispatchEvent(this.RECOMMENDATION_EVENTS.APPLIED, response.data);
    } else if (url?.includes('/dismiss')) {
      this.dispatchEvent(this.RECOMMENDATION_EVENTS.DISMISSED, response.data);
    }
  }

  private notifyError(error: Error): void {
    this.dispatchEvent(this.RECOMMENDATION_EVENTS.ERROR, { error: error.message });
  }

  private dispatchEvent(eventName: string, detail: unknown): void {
    window.dispatchEvent(new CustomEvent(eventName, { detail }));
  }

  // Core Recommendation Methods
  async getRecommendations(
    pipelineId: string,
    filters?: RecommendationFilters
  ): Promise<ApiResponse<Recommendation[]>> {
    return this.get(
      API_CONFIG.ENDPOINTS.RECOMMENDATIONS.LIST,
      { 
        routeParams: { id: pipelineId },
        params: filters 
      }
    );
  }

  async getRecommendationDetails(
    recommendationId: string
  ): Promise<ApiResponse<Recommendation>> {
    return this.get(
      API_CONFIG.ENDPOINTS.RECOMMENDATIONS.DETAILS,
      { routeParams: { id: recommendationId } }
    );
  }

  async applyRecommendation(
    recommendationId: string,
    actionId: string,
    parameters?: Record<string, unknown>
  ): Promise<ApiResponse<RecommendationHistory>> {
    return this.post(
      API_CONFIG.ENDPOINTS.RECOMMENDATIONS.APPLY,
      { actionId, parameters },
      { routeParams: { id: recommendationId } }
    );
  }

  async dismissRecommendation(
    recommendationId: string,
    reason?: string
  ): Promise<ApiResponse<void>> {
    return this.post(
      API_CONFIG.ENDPOINTS.RECOMMENDATIONS.DISMISS,
      { reason },
      { routeParams: { id: recommendationId } }
    );
  }

  async getApplicationStatus(
    recommendationId: string
  ): Promise<ApiResponse<RecommendationHistory>> {
    return this.get(
      API_CONFIG.ENDPOINTS.RECOMMENDATIONS.STATUS,
      { routeParams: { id: recommendationId } }
    );
  }

  async getRecommendationHistory(
    pipelineId: string
  ): Promise<ApiResponse<RecommendationHistory[]>> {
    return this.get(
      API_CONFIG.ENDPOINTS.RECOMMENDATIONS.HISTORY,
      { routeParams: { id: pipelineId } }
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

    while (Date.now() - startTime < timeout) {
      const response = await this.getApplicationStatus(recommendationId);
      const status = response.data.status;

      if (status === 'completed' || status === 'failed') {
        this.dispatchEvent(
          this.RECOMMENDATION_EVENTS.STATUS_CHANGE,
          { recommendationId, status }
        );
        return response.data;
      }

      await new Promise(resolve => setTimeout(resolve, interval));
    }

    throw new Error('Recommendation application timeout');
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

  async getRecommendationSummary(pipelineId: string): Promise<{
    pending: Recommendation[];
    applied: RecommendationHistory[];
    dismissed: RecommendationHistory[];
  }> {
    const [recommendations, history] = await Promise.all([
      this.getRecommendations(pipelineId),
      this.getRecommendationHistory(pipelineId)
    ]);

    return {
      pending: recommendations.data,
      applied: history.data.filter(h => h.status === 'completed'),
      dismissed: history.data.filter(h => h.status === 'dismissed')
    };
  }

  // Event Subscription
  subscribeToEvents(
    event: keyof typeof this.RECOMMENDATION_EVENTS,
    callback: (event: CustomEvent) => void
  ): () => void {
    const handler = (e: Event) => callback(e as CustomEvent);
    window.addEventListener(this.RECOMMENDATION_EVENTS[event], handler);
    return () => window.removeEventListener(this.RECOMMENDATION_EVENTS[event], handler);
  }
}

// Export singleton instance
export const recommendationsApi = new RecommendationsApi();