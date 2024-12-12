// src/analysis/types/analysis.ts
import { ImpactLevel } from '@/common';

// Core Analysis Types
export type AnalysisStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type AnalysisType = 'quality' | 'insight';

// Base Configuration Types
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

// Analysis Result Types
export interface AnalysisResult {
  id: string;
  type: AnalysisType;
  status: AnalysisStatus;
  progress: number;
  startedAt: string;
  completedAt?: string;
  error?: string;
  updatedAt: string;
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
  id: string;
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
  id: string;
  summary: {
    patternsFound: number;
    anomaliesDetected: number;
    correlationsIdentified: number;
    confidenceLevel: number;
  };
  patterns: Pattern[];
  anomalies: Anomaly[];
  correlations: Correlation[];
}

// Detailed Analysis Types
export interface Pattern {
  id: string;
  name: string;
  type: string;
  description: string;
  occurrenceRate: number;
  confidence: number;
  affectedFields: string[];
}

export interface Anomaly {
  id: string;
  type: string;
  severity: ImpactLevel;
  detectedAt: string;
  description: string;
}

export interface Correlation {
  id: string;
  sourceField: string;
  targetField: string;
  strength: number;
  confidence: number;
  description: string;
  columns: string[];
}

export interface Trend {
  id: string;
  name: string;
  direction: 'increasing' | 'decreasing' | 'stable';
  strength: number;
  timePeriod: string;
  description: string;
}

// Export & State Types
export interface ExportOptions {
  format: 'pdf' | 'csv' | 'json';
  sections?: string[];
  includeRecommendations?: boolean;
}

export interface AnalysisState {
  activeAnalyses: Record<string, {
    id: string;
    name: string;
    type: string;
    status: AnalysisStatus;
    progress: number;
    results: Record<string, unknown>;
    error?: string;
    startedAt: string;
    completedAt?: string;
  }>;
  history: Array<{
    id: string;
    type: string;
    parameters: Record<string, unknown>;
    results: Record<string, unknown>;
    createdAt: string;
  }>;
  isLoading: boolean;
  error: string | null;
}