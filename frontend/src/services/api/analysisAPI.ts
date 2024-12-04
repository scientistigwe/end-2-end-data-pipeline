// src/services/api/analysisApi.ts
import { api } from './client';
import { API_CONFIG } from './config';
import { AnalysisConfig, AnalysisType } from './types';

export interface QualityConfig extends AnalysisConfig {
  type: 'quality';
  rules?: {
    dataTypes?: boolean;
    nullChecks?: boolean;
    rangeValidation?: boolean;
    customRules?: Record<string, any>;
  };
  thresholds?: {
    errorThreshold?: number;
    warningThreshold?: number;
  };
}

export const analysisApi = {
  // Quality Analysis
  startQualityAnalysis: async (config: AnalysisConfig) => {
    return api.post(API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.START, config);
  },

  getQualityStatus: async (analysisId: string) => {
    return api.get(API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.STATUS, { id: analysisId });
  },

  getQualityReport: async (analysisId: string) => {
    return api.get(API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.REPORT, { id: analysisId });
  },

  // Insight Analysis
  startInsightAnalysis: async (config: AnalysisConfig) => {
    return api.post(API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.START, config);
  },

  getInsightStatus: async (analysisId: string) => {
    return api.get(API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.STATUS, { id: analysisId });
  },

  getInsightReport: async (analysisId: string) => {
    return api.get(API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.REPORT, { id: analysisId });
  },

  getInsightTrends: async (analysisId: string) => {
    return api.get(`${API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.TRENDS}/${analysisId}`);
  },

  getInsightPatternDetails: async (analysisId: string, patternId: string) => {
    return api.get(
      `${API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.PATTERN_DETAILS}/${analysisId}/${patternId}`
    );
  },

  exportInsights: async (analysisId: string, format: 'pdf' | 'csv' | 'json') => {
    return api.post(`${API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.EXPORT}/${analysisId}`, {
      format
    })
  },

  // Generic Analysis Operations
  cancelAnalysis: async (analysisId: string, type: AnalysisType) => {
    return api.post(`/analysis/${type}/${analysisId}/cancel`);
  },

  retryAnalysis: async (analysisId: string, type: AnalysisType) => {
    return api.post(`/analysis/${type}/${analysisId}/retry`);
  },
  getQualityIssuesSummary: async (analysisId: string) => {
    return api.get(`${API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.BASE}/${analysisId}/issues/summary`);
  },

  applyQualityFix: async (analysisId: string, issueId: string, fix: any) => {
    return api.post(
      `${API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.BASE}/${analysisId}/issues/${issueId}/fix`,
      { fix }
    )
  },
  cancelQualityAnalysis: async (analysisId: string) => {
    return api.post(`${API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.BASE}/${analysisId}/cancel`);
  },
};