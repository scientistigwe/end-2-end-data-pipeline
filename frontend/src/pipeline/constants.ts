// src/pipeline/constants.ts
export const PIPELINE_CONSTANTS = {
  STEPS: {
    TYPES: {
      TRANSFORM: 'transform',
      VALIDATE: 'validate',
      EXPORT: 'export',
      IMPORT: 'import',
      CUSTOM: 'custom'
    },
    MAX_RETRIES: 3,
    DEFAULT_TIMEOUT: 300000 // 5 minutes in milliseconds
  },
  
  STATUS: {
    IDLE: 'idle',
    RUNNING: 'running',
    PAUSED: 'paused',
    COMPLETED: 'completed',
    FAILED: 'failed',
    CANCELLED: 'cancelled'
  } as const,

  MODES: {
    DEVELOPMENT: 'development',
    STAGING: 'staging',
    PRODUCTION: 'production'
  } as const,

  LOG_LEVELS: {
    INFO: 'info',
    WARN: 'warn',
    ERROR: 'error'
  } as const,

  PAGINATION: {
    DEFAULT_PAGE_SIZE: 10,
    MAX_PAGE_SIZE: 100
  },

  METRICS: {
    REFRESH_INTERVAL: 30000, // 30 seconds
    RETENTION_PERIOD: 604800000 // 7 days in milliseconds
  },

  VALIDATION: {
    NAME_MIN_LENGTH: 3,
    NAME_MAX_LENGTH: 50,
    DESCRIPTION_MAX_LENGTH: 200,
    MAX_TAGS: 10,
    TAG_MAX_LENGTH: 20
  },

  UI: {
    LOG_VIEWER_HEIGHT: 600,
    METRICS_CHART_HEIGHT: 400,
    DEFAULT_CHART_PERIOD: '24h'
  }
} as const;

// Type guard for pipeline status
export function isPipelineStatus(status: string): status is PipelineStatus {
  return Object.values(PIPELINE_CONSTANTS.STATUS).includes(status as PipelineStatus);
}

// Type guard for pipeline mode
export function isPipelineMode(mode: string): mode is PipelineMode {
  return Object.values(PIPELINE_CONSTANTS.MODES).includes(mode as PipelineMode);
}

// Type guard for log level
export function isLogLevel(level: string): level is LogLevel {
  return Object.values(PIPELINE_CONSTANTS.LOG_LEVELS).includes(level as LogLevel);
}