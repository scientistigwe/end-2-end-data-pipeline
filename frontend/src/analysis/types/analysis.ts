// src/insight/types/insight.ts
import { z } from "zod";
import { ImpactLevel } from '@/common';

// Core Enums
export const AnalysisStatus = {
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
} as const;

export const AnalysisType = {
  QUALITY: 'quality',
  INSIGHT: 'insight'
} as const;

export type AnalysisStatus = typeof AnalysisStatus[keyof typeof AnalysisStatus];
export type AnalysisType = typeof AnalysisType[keyof typeof AnalysisType];

// Validation Schemas
export const analysisConfigSchema = z.object({
  pipelineId: z.string().min(1),
  type: z.enum(['quality', 'insight']),
  options: z.object({
    timeout: z.number().optional(),
    priority: z.enum(['low', 'medium', 'high']).optional(),
    retryAttempts: z.number().min(0).optional()
  }).optional()
});

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

// Custom Rule Types
export interface CustomRule {
  id: string;
  name: string;
  condition: string;
  parameters: Record<string, unknown>;
  enabled: boolean;
}

// Analysis Result Types
export interface AnalysisError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  timestamp: string;
}

export interface AnalysisResult {
  id: string;
  type: AnalysisType;
  status: AnalysisStatus;
  progress: number;
  startedAt: string;
  completedAt?: string;
  error?: AnalysisError;
  updatedAt: string;
  metadata?: Record<string, unknown>;
}

// Quality Analysis Types
export const qualityConfigSchema = analysisConfigSchema.extend({
  type: z.literal('quality'),
  rules: z.object({
    dataTypes: z.boolean().optional(),
    nullChecks: z.boolean().optional(),
    rangeValidation: z.boolean().optional(),
    customRules: z.record(z.any()).optional()
  }).optional(),
  thresholds: z.object({
    errorThreshold: z.number().min(0).max(100).optional(),
    warningThreshold: z.number().min(0).max(100).optional()
  }).optional()
});

export interface QualityConfig extends Omit<AnalysisConfig, 'type'> {
  type: 'quality';
  rules?: {
    dataTypes?: boolean;
    nullChecks?: boolean;
    rangeValidation?: boolean;
    customRules?: Record<string, CustomRule>;
  };
  thresholds?: {
    errorThreshold?: number;
    warningThreshold?: number;
  };
}

export interface QualityIssue {
  id: string;
  type: string;
  severity: 'critical' | 'warning' | 'info';
  description: string;
  affectedColumns: string[];
  possibleFixes?: Array<{
    id: string;
    description: string;
    impact: ImpactLevel;
    estimatedEffort: 'low' | 'medium' | 'high';
  }>;
  metadata?: Record<string, unknown>;
}

export interface QualityReport {
  id: string;
  summary: {
    totalIssues: number;
    criticalIssues: number;
    warningIssues: number;
    qualityScore?: number;
  };
  issues: QualityIssue[];
  recommendations: Array<{
    id: string;
    type: string;
    description: string;
    impact: ImpactLevel;
    priority: 'low' | 'medium' | 'high';
    estimatedEffort: 'low' | 'medium' | 'high';
  }>;
  metadata?: {
    generatedAt: string;
    version: string;
    environment: string;
    [key: string]: unknown;
  };
}

// Insight Analysis Types
export const insightConfigSchema = analysisConfigSchema.extend({
  type: z.literal('insight'),
  analysisTypes: z.object({
    patterns: z.boolean().optional(),
    correlations: z.boolean().optional(),
    anomalies: z.boolean().optional(),
    trends: z.boolean().optional()
  }).optional(),
  dataScope: z.object({
    columns: z.array(z.string()).optional(),
    timeRange: z.object({
      start: z.string(),
      end: z.string()
    }).optional()
  }).optional()
});

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
    analysisRange: {
      start: string;
      end: string;
    };
  };
  patterns: Pattern[];
  anomalies: Anomaly[];
  correlations: Correlation[];
  metadata?: Record<string, unknown>;
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
  metadata?: {
    discoveredAt: string;
    lastObserved: string;
    frequency: number;
    [key: string]: unknown;
  };
}

export interface Anomaly {
  id: string;
  type: string;
  severity: ImpactLevel;
  detectedAt: string;
  description: string;
  metadata?: {
    confidence: number;
    affectedRecords: number;
    [key: string]: unknown;
  };
}

export interface Correlation {
  id: string;
  sourceField: string;
  targetField: string;
  strength: number;
  confidence: number;
  description: string;
  columns: string[];
  metadata?: {
    analysisMethod: string;
    sampleSize: number;
    [key: string]: unknown;
  };
}

export interface Trend {
  id: string;
  name: string;
  direction: 'increasing' | 'decreasing' | 'stable';
  strength: number;
  timePeriod: string;
  description: string;
  metadata?: {
    confidence: number;
    seasonality?: boolean;
    [key: string]: unknown;
  };
}

// Export & State Types
export interface ExportOptions {
  format: 'pdf' | 'csv' | 'json';
  sections?: string[];
  includeRecommendations?: boolean;
  filters?: {
    severity?: ('critical' | 'warning' | 'info')[];
    confidence?: number;
    timeRange?: {
      start: string;
      end: string;
    };
  };
}

export interface AnalysisState {
  activeAnalyses: Record<string, {
    id: string;
    name: string;
    type: AnalysisType;
    status: AnalysisStatus;
    progress: number;
    results: Record<string, unknown>;
    error?: AnalysisError;
    startedAt: string;
    completedAt?: string;
    metadata?: Record<string, unknown>;
  }>;
  history: Array<{
    id: string;
    type: AnalysisType;
    parameters: Record<string, unknown>;
    results: Record<string, unknown>;
    createdAt: string;
    metadata?: Record<string, unknown>;
  }>;
  isLoading: boolean;
  error: string | null;
}