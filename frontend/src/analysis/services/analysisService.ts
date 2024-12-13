// src/analysis/services/analysisService.ts

import { analysisApi } from '../api/analysisApi';
import type {
  QualityConfig,
  InsightConfig,
  AnalysisResult,
  QualityReport,
  InsightReport,
  Pattern,
  Correlation,
  Anomaly,
  Trend,
  ExportOptions
} from '../types/analysis';

class AnalysisService {
  async startQualityAnalysis(config: QualityConfig): Promise<AnalysisResult> {
    try {
      const response = await analysisApi.startQualityAnalysis(config);
      return response.data;
    } catch (error) {
      throw new Error('Failed to start quality analysis');
    }
  }

  async startInsightAnalysis(config: InsightConfig): Promise<AnalysisResult> {
    try {
      const response = await analysisApi.startInsightAnalysis(config);
      return response.data;
    } catch (error) {
      throw new Error('Failed to start insight analysis');
    }
  }

  async getAnalysisStatus(analysisId: string): Promise<AnalysisResult> {
    try {
      const response = await analysisApi.getQualityStatus(analysisId);
      return response.data;
    } catch (error) {
      throw new Error('Failed to get analysis status');
    }
  }

  async getQualityReport(analysisId: string): Promise<QualityReport> {
    try {
      const response = await analysisApi.getQualityReport(analysisId);
      return response.data;
    } catch (error) {
      throw new Error('Failed to get quality report');
    }
  }

  async getInsightReport(analysisId: string): Promise<InsightReport> {
    try {
      const response = await analysisApi.getInsightReport(analysisId);
      return response.data;
    } catch (error) {
      throw new Error('Failed to get insight report');
    }
  }

  async getCorrelations(analysisId: string): Promise<Correlation[]> {
    try {
      const response = await analysisApi.getCorrelations(analysisId);
      return response.data;
    } catch (error) {
      throw new Error('Failed to get correlations');
    }
  }

  async getAnomalies(analysisId: string): Promise<Anomaly[]> {
    try {
      const response = await analysisApi.getAnomalies(analysisId);
      return response.data;
    } catch (error) {
      throw new Error('Failed to get anomalies');
    }
  }

  async getTrends(analysisId: string): Promise<Trend[]> {
    try {
      const response = await analysisApi.getTrends(analysisId);
      return response.data;
    } catch (error) {
      throw new Error('Failed to get trends');
    }
  }

  async getPatternDetails(analysisId: string, patternId: string): Promise<Pattern> {
    try {
      const response = await analysisApi.getPatternDetails(analysisId, patternId);
      return response.data;
    } catch (error) {
      throw new Error('Failed to get pattern details');
    }
  }

  async exportReport(
    analysisId: string, 
    type: 'quality' | 'insight',
    options: ExportOptions
  ): Promise<{ downloadUrl: string }> {
    try {
      const response = type === 'quality' 
        ? await analysisApi.exportQualityReport(analysisId, options)
        : await analysisApi.exportInsightReport(analysisId, options);
      return response.data;
    } catch (error) {
      throw new Error('Failed to export report');
    }
  }
}

export const analysisService = new AnalysisService();