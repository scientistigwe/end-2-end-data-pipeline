// src/types/analysis.ts
import { ImpactLevel } from './common';

export type AnalysisStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type AnalysisType = 'quality' | 'insight';

// Base Analysis Types
export interface BaseAnalysisOptions {
  timeout?: number;
  priority?: ImpactLevel;
  retryAttempts?: number;
}

export interface AnalysisConfig {
  pipelineId: string;
  type: AnalysisType;
  options?: BaseAnalysisOptions;
}

export interface AnalysisResult {
  id: string;
  type: AnalysisType;
  status: AnalysisStatus;
  progress: number;
  startedAt: string;
  completedAt?: string;
  error?: string;
}

// Quality Analysis Types
export interface QualityConfig extends Omit<AnalysisConfig, 'type'> {
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

export interface QualityReport {
  summary: {
    totalIssues: number;
    criticalIssues: number;
    warningIssues: number;
  };
  issues: Array<{
    id: string;
    type: string;
    severity: 'critical' | 'warning' | 'info';
    description: string;
    affectedColumns: string[];
    possibleFixes?: Array<{
      id: string;
      description: string;
      impact: ImpactLevel;
    }>;
  }>;
  recommendations: Array<{
    id: string;
    type: string;
    description: string;
    impact: ImpactLevel;
  }>;
}

// Insight Analysis Types
export interface InsightConfig extends Omit<AnalysisConfig, 'type'> {
  type: 'insight';
  analysisTypes?: {
    patterns?: boolean;
    correlations?: boolean;
    anomalies?: boolean;
    trends?: boolean;
  };
  dataScope?: {
    columns?: string[];
    timeRange?: {
      start: string;
      end: string;
    };
  };
}

export interface InsightReport {
  summary: {
    patternsFound: number;
    anomaliesDetected: number;
    correlationsIdentified: number;
  };
  patterns: Array<{
    id: string;
    type: string;
    description: string;
    confidence: number;
    affectedColumns: string[];
  }>;
  anomalies: Array<{
    id: string;
    type: string;
    description: string;
    severity: ImpactLevel;
    timestamp: string;
  }>;
  correlations: Array<{
    columns: string[];
    strength: number;
    description: string;
  }>;
}

export interface ExportOptions {
  format: 'pdf' | 'csv' | 'json';
  sections?: string[];
  includeRecommendations?: boolean;
}