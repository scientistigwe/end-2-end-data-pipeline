// src/analysis/utils/formatters.ts
import { dateUtils } from "@/common";
import type { 
  AnalysisStatus, 
  QualityConfig, 
  InsightConfig 
} from "../types/analysis";

export const formatAnalysisConfig = (
  config: QualityConfig | InsightConfig
): string => {
  const baseInfo = `Pipeline: ${config.pipelineId}`;
  
  if (config.type === 'quality') {
    const rules = Object.entries(config.rules || {})
      .filter(([_, enabled]) => enabled)
      .map(([rule]) => rule)
      .join(', ');
    
    return `${baseInfo}\nRules: ${rules || 'None'}\nThresholds: Error ${
      config.thresholds?.errorThreshold || 0
    }%, Warning ${config.thresholds?.warningThreshold || 0}%`;
  }
  
  const types = Object.entries(config.analysisTypes || {})
    .filter(([_, enabled]) => enabled)
    .map(([type]) => type)
    .join(', ');
  
  const timeRange = config.dataScope?.timeRange;
  const timeInfo = timeRange 
    ? `\nTime Range: ${dateUtils.formatDate(timeRange.start)} - ${dateUtils.formatDate(timeRange.end)}`
    : '';
  
  return `${baseInfo}\nTypes: ${types || 'None'}${timeInfo}`;
};

export const getStatusColor = (status: AnalysisStatus): string => {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800';
    case 'running':
      return 'bg-blue-100 text-blue-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    case 'cancelled':
      return 'bg-gray-100 text-gray-800';
    default:
      return 'bg-yellow-100 text-yellow-800';
  }
};

export const getStatusBadgeClass = (status: AnalysisStatus): string => {
  switch (status) {
    case 'completed':
      return 'border-green-500 text-green-700';
    case 'running':
      return 'border-blue-500 text-blue-700';
    case 'failed':
      return 'border-red-500 text-red-700';
    case 'cancelled':
      return 'border-gray-500 text-gray-700';
    default:
      return 'border-yellow-500 text-yellow-700';
  }
};

export const formatMetricValue = (value: number, type: string): string => {
  switch (type) {
    case 'percentage':
      return `${(value * 100).toFixed(1)}%`;
    case 'count':
      return value.toLocaleString();
    case 'duration':
      return dateUtils.formatDetailedDuration(value);
    case 'confidence':
      return `${value.toFixed(1)}%`;
    default:
      return value.toFixed(2);
  }
};

export const getConfidenceLevelColor = (confidence: number): string => {
  if (confidence >= 90) return 'text-green-600';
  if (confidence >= 70) return 'text-blue-600';
  if (confidence >= 50) return 'text-yellow-600';
  return 'text-red-600';
};

export const formatAnalysisDuration = (
  startTime: string, 
  endTime?: string
): string => {
  if (!endTime) return 'In Progress';
  
  const start = new Date(startTime).getTime();
  const end = new Date(endTime).getTime();
  return dateUtils.formatDetailedDuration(end - start);
};