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
  },

  // Add RUNS configuration
  RUNS: {
    REFRESH: {
      INTERVAL: 10000,          // 10 seconds
      ACTIVE_INTERVAL: 5000,    // 5 seconds for active runs
      STALE_TIME: 5000         // 5 seconds
    },
    RETENTION: {
      PERIOD: 2592000000,      // 30 days in milliseconds
      MAX_RUNS: 1000           // Maximum number of runs to retain
    },
    SORTING: {
      FIELDS: {
        STARTED_AT: 'startedAt',
        COMPLETED_AT: 'completedAt',
        DURATION: 'duration'
      },
      ORDERS: {
        ASC: 'asc',
        DESC: 'desc'
      }
    } as const,
    RETRY: {
      COUNT: 3,
      MAX_ATTEMPTS: 5
    },
    PAGINATION: {
      DEFAULT_SIZE: 10,
      MAX_SIZE: 100
    }
  } as const
} as const;

// Type guards for pipeline status
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

// Add type guard for run sort fields
export function isRunSortField(field: string): field is RunSortField {
  return Object.values(PIPELINE_CONSTANTS.RUNS.SORTING.FIELDS).includes(field as RunSortField);
}

// Type definitions for the constants
export type PipelineStatus = typeof PIPELINE_CONSTANTS.STATUS[keyof typeof PIPELINE_CONSTANTS.STATUS];
export type PipelineMode = typeof PIPELINE_CONSTANTS.MODES[keyof typeof PIPELINE_CONSTANTS.MODES];
export type LogLevel = typeof PIPELINE_CONSTANTS.LOG_LEVELS[keyof typeof PIPELINE_CONSTANTS.LOG_LEVELS];
export type RunSortField = typeof PIPELINE_CONSTANTS.RUNS.SORTING.FIELDS[keyof typeof PIPELINE_CONSTANTS.RUNS.SORTING.FIELDS];
export type RunSortOrder = typeof PIPELINE_CONSTANTS.RUNS.SORTING.ORDERS[keyof typeof PIPELINE_CONSTANTS.RUNS.SORTING.ORDERS];