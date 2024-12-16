// src/analysis/api/analysisApi.ts
import { BaseClient } from '@/common/api/client/baseClient';
import { API_CONFIG } from '@/common/api/client/config';
import type { ApiResponse } from '@/common/types/api';
import type {
  QualityConfig,
  InsightConfig,
  AnalysisResult,
  QualityReport,
  InsightReport,
  ExportOptions
} from '../types/analysis';

class AnalysisApi extends BaseClient {
  constructor() {
    super({
      baseURL: import.meta.env.VITE_ANALYSIS_API_URL || API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        ...API_CONFIG.DEFAULT_HEADERS,
        'X-Service': 'analysis'
      }
    });
  }

  // Quality Analysis Methods
  async startQualityAnalysis(config: QualityConfig): Promise<ApiResponse<AnalysisResult>> {
    return this.post(
      API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.START,
      config
    );
  }

  async getQualityStatus(analysisId: string): Promise<ApiResponse<AnalysisResult>> {
    return this.get(
      API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.STATUS,
      { routeParams: { id: analysisId } }
    );
  }

  async getQualityReport(analysisId: string): Promise<ApiResponse<QualityReport>> {
    return this.get(
      API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.REPORT,
      { routeParams: { id: analysisId } }
    );
  }

  async exportQualityReport(
    analysisId: string,
    options: ExportOptions
  ): Promise<ApiResponse<{ downloadUrl: string }>> {
    return this.post(
      API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.EXPORT,
      options,
      {
        routeParams: { id: analysisId },
        responseType: 'blob'
      }
    );
  }

  // Insight Analysis Methods
  async startInsightAnalysis(config: InsightConfig): Promise<ApiResponse<AnalysisResult>> {
    return this.post(
      API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.START,
      config
    );
  }

  async getInsightStatus(analysisId: string): Promise<ApiResponse<AnalysisResult>> {
    return this.get(
      API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.STATUS,
      { routeParams: { id: analysisId } }
    );
  }

  async getInsightReport(analysisId: string): Promise<ApiResponse<InsightReport>> {
    return this.get(
      API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.REPORT,
      { routeParams: { id: analysisId } }
    );
  }

  async getCorrelations(
    analysisId: string
  ): Promise<ApiResponse<InsightReport['correlations']>> {
    return this.get(
      API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.CORRELATIONS,
      { routeParams: { id: analysisId } }
    );
  }

  async getAnomalies(
    analysisId: string
  ): Promise<ApiResponse<InsightReport['anomalies']>> {
    return this.get(
      API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.ANOMALIES,
      { routeParams: { id: analysisId } }
    );
  }

  async getTrends(
    analysisId: string
  ): Promise<ApiResponse<Array<{
    trend: string;
    significance: number;
    description: string;
  }>>> {
    return this.get(
      API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.TRENDS,
      { routeParams: { id: analysisId } }
    );
  }

  async getPatternDetails(
    analysisId: string,
    patternId: string
  ): Promise<ApiResponse<InsightReport['patterns'][0]>> {
    return this.get(
      API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.PATTERN_DETAILS,
      { routeParams: { id: analysisId, patternId } }
    );
  }

  async exportInsightReport(
    analysisId: string,
    options: ExportOptions
  ): Promise<ApiResponse<{ downloadUrl: string }>> {
    return this.post(
      API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.EXPORT,
      options,
      {
        routeParams: { id: analysisId },
        responseType: 'blob'
      }
    );
  }

  // Helper Methods
  async uploadAnalysisData(
    data: FormData,
    onProgress?: (progress: number) => void
  ) {
    return this.post<{ id: string }>(
      '/analysis/upload',
      data,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: onProgress ? 
          (progressEvent: ProgressEvent) => {
            if (progressEvent.lengthComputable) {
              const progress = (progressEvent.loaded / progressEvent.total) * 100;
              onProgress(Math.round(progress));
            }
          } : undefined
      }
    );
  }

  async checkAnalysisStatus(analysisId: string): Promise<'running' | 'completed' | 'failed'> {
    try {
      const response = await this.getQualityStatus(analysisId);
      return response.data.status;
    } catch (error) {
      console.error('Failed to check analysis status:', error);
      return 'failed';
    }
  }

  async cancelAnalysis(analysisId: string): Promise<ApiResponse<void>> {
    return this.post(
      `/analysis/${analysisId}/cancel`,
      null,
      { routeParams: { id: analysisId } }
    );
  }
}

// Export singleton instance
export const analysisApi = new AnalysisApi();