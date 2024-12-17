// src/analysis/api/analysisApi.ts
import { BaseClient } from '@/common/api/client/baseClient';
import { API_CONFIG } from '@/common/api/client/config';
import { RouteHelper } from '@/common/api/routes';
import type { AxiosProgressEvent } from 'axios';
import type { ApiResponse } from '@/common/types/api';
import type {
  QualityConfig,
  InsightConfig,
  AnalysisResult,
  QualityReport,
  InsightReport,
  ExportOptions,
  AnalysisStatus
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
      RouteHelper.getNestedRoute('ANALYSIS', 'QUALITY', 'START'),
      config
    );
  }

  async getQualityStatus(analysisId: string): Promise<ApiResponse<AnalysisResult>> {
    return this.get(
      RouteHelper.getNestedRoute('ANALYSIS', 'QUALITY', 'STATUS', { id: analysisId })
    );
  }

  async getQualityReport(analysisId: string): Promise<ApiResponse<QualityReport>> {
    return this.get(
      RouteHelper.getNestedRoute('ANALYSIS', 'QUALITY', 'REPORT', { id: analysisId })
    );
  }

  async exportQualityReport(
    analysisId: string,
    options: ExportOptions
  ): Promise<ApiResponse<{ downloadUrl: string }>> {
    return this.post(
      RouteHelper.getNestedRoute('ANALYSIS', 'QUALITY', 'EXPORT', { id: analysisId }),
      options,
      { responseType: 'blob' }
    );
  }

  // Insight Analysis Methods
  async startInsightAnalysis(config: InsightConfig): Promise<ApiResponse<AnalysisResult>> {
    return this.post(
      RouteHelper.getNestedRoute('ANALYSIS', 'INSIGHT', 'START'),
      config
    );
  }

  async getInsightStatus(analysisId: string): Promise<ApiResponse<AnalysisResult>> {
    return this.get(
      RouteHelper.getNestedRoute('ANALYSIS', 'INSIGHT', 'STATUS', { id: analysisId })
    );
  }

  async getInsightReport(analysisId: string): Promise<ApiResponse<InsightReport>> {
    return this.get(
      RouteHelper.getNestedRoute('ANALYSIS', 'INSIGHT', 'REPORT', { id: analysisId })
    );
  }

  async getCorrelations(
    analysisId: string
  ): Promise<ApiResponse<InsightReport['correlations']>> {
    return this.get(
      RouteHelper.getNestedRoute('ANALYSIS', 'INSIGHT', 'CORRELATIONS', { id: analysisId })
    );
  }

  async getAnomalies(
    analysisId: string
  ): Promise<ApiResponse<InsightReport['anomalies']>> {
    return this.get(
      RouteHelper.getNestedRoute('ANALYSIS', 'INSIGHT', 'ANOMALIES', { id: analysisId })
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
      RouteHelper.getNestedRoute('ANALYSIS', 'INSIGHT', 'TRENDS', { id: analysisId })
    );
  }

  async getPatternDetails(
    analysisId: string,
    patternId: string
  ): Promise<ApiResponse<InsightReport['patterns'][0]>> {
    return this.get(
      RouteHelper.getNestedRoute('ANALYSIS', 'INSIGHT', 'PATTERN_DETAILS', { 
        id: analysisId, 
        patternId 
      })
    );
  }

  async exportInsightReport(
    analysisId: string,
    options: ExportOptions
  ): Promise<ApiResponse<{ downloadUrl: string }>> {
    return this.post(
      RouteHelper.getNestedRoute('ANALYSIS', 'INSIGHT', 'EXPORT', { id: analysisId }),
      options,
      { responseType: 'blob' }
    );
  }

  // Helper Methods
  async uploadAnalysisData(
    data: FormData,
    onProgress?: (progress: number) => void
  ): Promise<ApiResponse<{ id: string }>> {
    return this.post(
      RouteHelper.getRoute('ANALYSIS', 'UPLOAD'),
      data,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent: AxiosProgressEvent) => {
          if (progressEvent.total) {
            const progress = (progressEvent.loaded / progressEvent.total) * 100;
            onProgress?.(Math.round(progress));
          }
        }
      }
    );
  }

  async checkAnalysisStatus(analysisId: string): Promise<AnalysisStatus> {
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
      RouteHelper.getRoute('ANALYSIS', 'CANCEL', { id: analysisId })
    );
  }
}

// Export singleton instance
export const analysisApi = new AnalysisApi();