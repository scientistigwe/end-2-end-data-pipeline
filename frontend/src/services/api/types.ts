// src/services/api/types.ts
import { AxiosError } from 'axios';

export type UserRole = 'user' | 'admin' | 'manager';

// Insight Analysis Types
export interface InsightAnalysisTypes {
  patterns?: boolean;
  correlations?: boolean;
  anomalies?: boolean;
  trends?: boolean;
}

export interface TimeRange {
  start: string;
  end: string;
}

export interface DataScope {
  columns?: string[];
  timeRange?: TimeRange;
}

// API Base Types
export interface ApiError {
  code: string;
  message: string;
  details?: any;
  status?: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
  message?: string;
  status: number;
}

// Auth Types
export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  permissions: string[];
}

export interface AuthPayload {
  token: string;
  refreshToken: string;
  user: User;
}

export interface AnalysisConfig {
  pipelineId: string;
  type: AnalysisType;
  options?: {
    timeout?: number;
    priority?: 'high' | 'medium' | 'low';
  };
}

export interface InsightConfig extends AnalysisConfig {
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

export interface QualityConfig extends AnalysisConfig {
  rules?: {
    completeness?: boolean;
    accuracy?: boolean;
    consistency?: boolean;
    uniqueness?: boolean;
  };
  thresholds?: {
    completeness?: number;
    accuracy?: number;
    consistency?: number;
    uniqueness?: number;
  };
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
    severity: 'high' | 'medium' | 'low';
    timestamp: string;
  }>;
  correlations: Array<{
    columns: string[];
    strength: number;
    description: string;
  }>;
  trends?: Array<{
    metric: string;
    trend: 'increasing' | 'decreasing' | 'stable';
    confidence: number;
    period: {
      start: string;
      end: string;
    };
  }>;
}

export interface QualityReport {
  summary: {
    overallScore: number;
    totalIssues: number;
    criticalIssues: number;
  };
  metrics: {
    completeness: number;
    accuracy: number;
    consistency: number;
    uniqueness: number;
  };
  issues: Array<{
    id: string;
    type: string;
    severity: 'critical' | 'major' | 'minor';
    description: string;
    affectedRows: number;
    suggestion?: string;
  }>;
}

// Error Handling Types
export type ApiErrorHandler = (error: AxiosError | ApiError) => void;

export interface ErrorResponse {
  error: ApiError;
  status: number;
}

// Utility Types
export interface PaginationParams {
  page: number;
  limit: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> extends ApiResponse<T> {
  pagination: {
    total: number;
    page: number;
    limit: number;
    totalPages: number;
  };
}

// Export function types
export type ApiErrorFormatter = (error: unknown) => ApiError;
export type ApiResponseFormatter = <T>(data: T) => ApiResponse<T>;


// Base Analysis Types
export type AnalysisStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type AnalysisType = 'quality' | 'insight' | 'performance';
export type AnalysisPriority = 'high' | 'medium' | 'low';
export type AnalysisSeverity = 'high' | 'medium' | 'low';
export type ExportFormat = 'pdf' | 'csv' | 'json';

export interface BaseAnalysisOptions {
  timeout?: number;
  priority?: AnalysisPriority;
}

export interface AnalysisConfig {
  type: AnalysisType;
  pipelineId: string;
  options?: BaseAnalysisOptions;
}