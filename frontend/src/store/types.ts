// src/store/types.ts

// Pipeline Types
type PipelineStatus = 'idle' | 'running' | 'paused' | 'completed' | 'error';
type PipelineType = 'etl' | 'transformation' | 'validation' | 'custom';
type StepStatus = 'pending' | 'running' | 'completed' | 'error';

// Base interface for DataSource
interface DataSourceState {
  activeSources: Record<string, {
    id: string;
    type: 'file' | 'api' | 'database' | 's3' | 'stream';
    status: 'connecting' | 'connected' | 'error' | 'disconnected';
    config: any;
    metadata: any;
    error?: string;
  }>;
  sourceConfigurations: Record<string, any>;
  uploadProgress: Record<string, number>;
  connectionHistory: Array<{
    id: string;
    type: string;
    timestamp: string;
    status: string;
  }>;
}

interface PipelineStep {
  id: string;
  name: string;
  type: string;
  status: StepStatus;
  startTime?: string;
  endTime?: string;
  error?: string;
  metadata?: Record<string, any>;
}

interface PipelineConfig {
  name: string;
  type: PipelineType;
  description?: string;
  steps: PipelineStep[];
  sourceId: string;
  targetId?: string;
  schedule?: {
    enabled: boolean;
    cron?: string;
    lastRun?: string;
    nextRun?: string;
  };
  retryConfig?: {
    maxAttempts: number;
    backoffMultiplier: number;
  };
}

interface Pipeline {
  id: string;
  name: string;  // This is required
  status: PipelineStatus;
  progress: number;
  sourceId: string;
  config: PipelineConfig;
  metadata: Record<string, any>;
  error?: string;
  startTime: string;
  endTime?: string;
  currentStep?: string;
  attempts: number;
}

interface PipelineHistoryEntry {
  id: string;
  pipelineId: string;
  startTime: string;
  endTime?: string;
  status: PipelineStatus;
  error?: string;
  metrics?: {
    duration: number;
    processedRecords: number;
    failedRecords: number;
  };
}

interface PipelineState {
  activePipelines: Record<string, Pipeline>;
  pipelineHistory: PipelineHistoryEntry[];
  configurations: Record<string, PipelineConfig>;
  currentPipeline: string | null;
  loading: boolean;
  error: string | null;
}


interface AnalysisState {
  analyses: Record<string, {
    id: string;
    type: string;
    status: 'running' | 'completed' | 'error';
    results: any;
  }>;
  activeAnalysis: string | null;
}

interface MonitoringState {
  metrics: Record<string, any>;
  alerts: Array<{
    id: string;
    type: string;
    severity: 'low' | 'medium' | 'high';
    message: string;
    timestamp: string;
  }>;
  dashboards: Record<string, any>;
}

interface RecommendationsState {
  suggestions: Array<{
    id: string;
    type: string;
    priority: 'low' | 'medium' | 'high';
    description: string;
    implemented: boolean;
  }>;
}

interface ReportState {
  reports: Record<string, {
    id: string;
    type: string;
    data: any;
    generatedAt: string;
  }>;
  activeReport: string | null;
}

interface UIState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  activeModal: string | null;
  notifications: Array<{
    id: string;
    type: 'info' | 'success' | 'warning' | 'error';
    message: string;
  }>;
}

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: {
    id: string;
    email: string;
    role: string;
    permissions: string[];
  } | null;
  isAuthenticated: boolean;
}

// Export all state interfaces for use in slices
export type {
  DataSourceState,
  AnalysisState,
  MonitoringState,
  RecommendationsState,
  ReportState,
  UIState,
  AuthState,
  PipelineState,
  Pipeline,
  PipelineConfig,
  PipelineStep,
  PipelineStatus,
  PipelineType,
  StepStatus,
  PipelineHistoryEntry

};