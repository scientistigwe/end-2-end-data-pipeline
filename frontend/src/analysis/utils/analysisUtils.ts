// src/analysis/utils/analysisUtils.ts

import { ANALYSIS_CONSTANTS } from '../constants';
import type { 
  AnalysisResult, 
  QualityConfig, 
  InsightConfig,
  Correlation,
  Anomaly 
} from '../types/analysis';
import { dateUtils } from '@/common';

export const validateAnalysisConfig = (
  config: QualityConfig | InsightConfig
): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (!config.pipelineId) {
    errors.push('Pipeline ID is required');
  }

  if (config.type === 'quality') {
    const { thresholds } = config;
    if (thresholds) {
      if (thresholds.errorThreshold < ANALYSIS_CONSTANTS.THRESHOLDS.ERROR.MIN || 
          thresholds.errorThreshold > ANALYSIS_CONSTANTS.THRESHOLDS.ERROR.MAX) {
        errors.push('Invalid error threshold');
      }
      if (thresholds.warningThreshold < ANALYSIS_CONSTANTS.THRESHOLDS.WARNING.MIN || 
          thresholds.warningThreshold > ANALYSIS_CONSTANTS.THRESHOLDS.WARNING.MAX) {
        errors.push('Invalid warning threshold');
      }
    }
  } else {
    const { dataScope } = config;
    if (dataScope?.timeRange) {
      const { start, end } = dataScope.timeRange;
      if (!dateUtils.isValidDate(start) || !dateUtils.isValidDate(end)) {
        errors.push('Invalid date range');
      }
      if (new Date(end) <= new Date(start)) {
        errors.push('End date must be after start date');
      }
    }
  }

  return {
    isValid: errors.length === 0,
    errors
  };
};

export const calculateProgress = (result: AnalysisResult): number => {
  if (result.status === 'completed') return 100;
  if (result.status === 'failed' || result.status === 'cancelled') return 0;
  
  const startTime = new Date(result.startedAt).getTime();
  const now = Date.now();
  const duration = now - startTime;
  
  // Estimate progress based on typical analysis duration
  const typicalDuration = 5 * 60 * 1000; // 5 minutes
  return Math.min(Math.round((duration / typicalDuration) * 100), 99);
};

export const shouldRetryAnalysis = (
  result: AnalysisResult,
  attempts: number
): boolean => {
  if (attempts >= ANALYSIS_CONSTANTS.MAX_RETRIES) return false;
  if (result.status === 'failed') {
    // Check if error is retryable
    const nonRetryableErrors = [
      'configuration error',
      'invalid input',
      'unauthorized'
    ];
    return !nonRetryableErrors.some(err => 
      result.error?.toLowerCase().includes(err)
    );
  }
  return false;
};

export const calculateCorrelationStrength = (
  correlations: Correlation[]
): number => {
  if (!correlations.length) return 0;
  return correlations.reduce(
    (avg, curr) => avg + curr.strength, 
    0
  ) / correlations.length;
};

export const groupAnomaliesBySeverity = (
  anomalies: Anomaly[]
): Record<string, Anomaly[]> => {
  return anomalies.reduce((groups, anomaly) => {
    const severity = anomaly.severity;
    return {
      ...groups,
      [severity]: [...(groups[severity] || []), anomaly]
    };
  }, {} as Record<string, Anomaly[]>);
};

export const calculateAnalysisMetrics = (result: AnalysisResult) => {
  const duration = result.completedAt 
    ? dateUtils.formatDetailedDuration(
        new Date(result.completedAt).getTime() - 
        new Date(result.startedAt).getTime()
      )
    : null;

  return {
    duration,
    status: result.status,
    progress: calculateProgress(result),
    error: result.error,
    startTime: dateUtils.formatDate(result.startedAt, { includeTime: true }),
    endTime: result.completedAt 
      ? dateUtils.formatDate(result.completedAt, { includeTime: true })
      : null
  };
};

export const downloadAnalysisReport = async (
  report: Blob,
  filename: string
): Promise<void> => {
  const url = window.URL.createObjectURL(report);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};