// src/services/api/analysisApi.ts
import { BaseApiClient } from './client';
import { API_CONFIG } from './config';
import type { ApiResponse } from '../../types/api';
import type {
  QualityConfig,
  InsightConfig,
  AnalysisResult,
  QualityReport,
  InsightReport,
  ExportOptions
} from '../../types/analysis';

class AnalysisApi extends BaseApiClient {
  // Quality Analysis
  async startQualityAnalysis(
    config: QualityConfig
  ): Promise<ApiResponse<AnalysisResult>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.START,
      {},
      config
    );
  }

  async getQualityStatus(
    analysisId: string
  ): Promise<ApiResponse<AnalysisResult>> {
    return this.request('get', API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.STATUS, {
      routeParams: { id: analysisId }
    });
  }

  async getQualityReport(
    analysisId: string
  ): Promise<ApiResponse<QualityReport>> {
    return this.request('get', API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.REPORT, {
      routeParams: { id: analysisId }
    });
  }

  async exportQualityReport(
    analysisId: string,
    options: ExportOptions
  ): Promise<ApiResponse<{ downloadUrl: string }>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.EXPORT,
      {
        routeParams: { id: analysisId }
      },
      options
    );
  }

  // Insight Analysis
  async startInsightAnalysis(
    config: InsightConfig
  ): Promise<ApiResponse<AnalysisResult>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.START,
      {},
      config
    );
  }

  async getInsightStatus(
    analysisId: string
  ): Promise<ApiResponse<AnalysisResult>> {
    return this.request('get', API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.STATUS, {
      routeParams: { id: analysisId }
    });
  }

  async getInsightReport(
    analysisId: string
  ): Promise<ApiResponse<InsightReport>> {
    return this.request('get', API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.REPORT, {
      routeParams: { id: analysisId }
    });
  }

  async getCorrelations(
    analysisId: string
  ): Promise<ApiResponse<InsightReport['correlations']>> {
    return this.request('get', API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.CORRELATIONS, {
      routeParams: { id: analysisId }
    });
  }

  async getAnomalies(
    analysisId: string
  ): Promise<ApiResponse<InsightReport['anomalies']>> {
    return this.request('get', API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.ANOMALIES, {
      routeParams: { id: analysisId }
    });
  }

  async getTrends(
    analysisId: string
  ): Promise<ApiResponse<Array<{
    trend: string;
    significance: number;
    description: string;
  }>>> {
    return this.request('get', API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.TRENDS, {
      routeParams: { id: analysisId }
    });
  }

  async getPatternDetails(
    analysisId: string,
    patternId: string
  ): Promise<ApiResponse<InsightReport['patterns'][0]>> {
    return this.request(
      'get',
      API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.PATTERN_DETAILS,
      {
        routeParams: { id: analysisId, patternId }
      }
    );
  }

  async exportInsightReport(
    analysisId: string,
    options: ExportOptions
  ): Promise<ApiResponse<{ downloadUrl: string }>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.EXPORT,
      {
        routeParams: { id: analysisId }
      },
      options
    );
  }
}

export const analysisApi = new AnalysisApi();