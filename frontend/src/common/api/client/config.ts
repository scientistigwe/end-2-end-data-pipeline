// src/common/api/config.ts
import type { 
  AxiosRequestConfig, 
  AxiosProgressEvent 
} from 'axios';

export const API_CONFIG = {
  BASE_URL: import.meta.env.REACT_APP_API_URL || '/api/v1',
  TIMEOUT: 30000,
  RETRY_COUNT: 3,
  DEFAULT_HEADERS: {
    'Content-Type': 'application/json'
  },
  
  ENDPOINTS: {
    // Auth Endpoints
    AUTH: { 
      LOGIN: '/auth/login',
      REGISTER: '/auth/register',  
      REFRESH: '/auth/refresh',
      LOGOUT: '/auth/logout',
      VERIFY: '/auth/verify',
      FORGOT_PASSWORD: '/auth/forgot-password',
      RESET_PASSWORD: '/auth/reset-password',
      VERIFY_EMAIL: '/auth/verify-email',
      PROFILE: '/auth/profile',
      CHANGE_PASSWORD: '/auth/change-password'
    },

    // Data source endpoints
    DATA_SOURCES: {
      LIST: '/sources',
      CREATE: '/sources',
      GET: '/sources/:id',
      UPDATE: '/sources/:id',
      DELETE: '/sources/:id',
      TEST: '/sources/:id/test',
      SYNC: '/sources/:id/sync',
      VALIDATE: '/sources/:id/validate',
      PREVIEW: '/sources/:id/preview',
      DISCONNECT: '/sources/connection/:connectionId/disconnect',
      STATUS: '/sources/connection/:connectionId/status',

      API: {
        CONNECT: '/sources/api/connect',
        TEST: '/sources/api/test-endpoint',
        EXECUTE: '/sources/api/:connectionId/execute',
        STATUS: '/sources/api/:connectionId/status',
        METADATA: '/sources/api/metadata'
      },

      DATABASE: {
        CONNECT: '/sources/database/connect',
        TEST: '/sources/database/:connectionId/test',
        QUERY: '/sources/database/:connectionId/query',
        SCHEMA: '/sources/database/:connectionId/schema',
        STATUS: '/sources/database/:connectionId/status',
        METADATA: '/sources/database/metadata'
      },

      S3: {
        CONNECT: '/sources/s3/connect',
        LIST: '/sources/s3/:connectionId/list',
        INFO: '/sources/s3/:connectionId/info',
        DOWNLOAD: '/sources/s3/:connectionId/download',
        STATUS: '/sources/s3/:connectionId/status',
        METADATA: '/sources/s3/metadata'
      },

      STREAM: {
        CONNECT: '/sources/stream/connect',
        STATUS: '/sources/stream/:connectionId/status',
        METRICS: '/sources/stream/:connectionId/metrics',
        START: '/sources/stream/start',
        STOP: '/sources/stream/stop',
        METADATA: '/sources/stream/metadata'
      },

      FILE: {
        UPLOAD: '/sources/file/upload',
        PARSE: '/sources/file/:fileId/parse',
        METADATA: '/sources/file/:fileId/metadata'
      }
    },
    
    // Pipeline endpoints
    PIPELINES: {
      LIST: '/pipelines',
      CREATE: '/pipelines',
      GET: '/pipelines/:id',
      UPDATE: '/pipelines/:id',
      DELETE: '/pipelines/:id',
      START: '/pipelines/:id/start',
      STOP: '/pipelines/:id/stop',
      STATUS: '/pipelines/:id/status',
      LOGS: '/pipelines/:id/logs',
      PAUSE: '/pipelines/pause',
      RESUME: '/pipelines/resume',
      RETRY: '/pipelines/retry',
      METRICS: '/pipelines/metrics',
      RUNS: '/pipelines/runs',
      VALIDATE: '/pipelines/validate'

    },

    // Analysis endpoints
    ANALYSIS: {
      QUALITY: {
        START: '/analysis/quality/start',
        STATUS: '/analysis/quality/:id',  // Base path for quality analysis
        REPORT: '/analysis/quality/:id/report',
        EXPORT: '/analysis/quality/:id/export'
      },
      INSIGHT: {
        START: '/analysis/insight/start',
        STATUS: '/analysis/insight/:id',  // Base path for insight analysis
        REPORT: '/analysis/insight/:id/report',
        TRENDS: '/analysis/insight/:id/trends',
        PATTERN_DETAILS: '/analysis/insight/:id/pattern/:patternId',
        EXPORT: '/analysis/insight/:id/export',
        CORRELATIONS: '/analysis/insight/:id/correlations',
        ANOMALIES: '/analysis/insight/:id/anomalies'
      }
    },
    
    // Monitoring endpoints
    MONITORING: {
      START: '/monitoring/:id/start',
      METRICS: '/monitoring/:id/metrics',
      HEALTH: '/monitoring/:id/health',
      PERFORMANCE: '/monitoring/:id/performance',
      ALERTS_CONFIG: '/monitoring/:id/alerts/config',
      ALERTS_HISTORY: '/monitoring/:id/alerts/history',
      RESOURCES: '/monitoring/:id/resources',
      TIME_SERIES: '/monitoring/:id/time-series',
      AGGREGATED: '/monitoring/:id/metrics/aggregated'
    },
    
    // Reports endpoints
    REPORTS: {
      LIST: '/reports',
      CREATE: '/reports',
      GET: '/reports/:id',
      STATUS: '/reports/:id/status',
      DELETE: '/reports/:id',
      EXPORT: '/reports/:id/export',
      SCHEDULE: '/reports/schedule',
      METADATA: '/reports/:id/metadata',
      PREVIEW: '/reports/:id/preview',
      TEMPLATES: '/reports/templates',
      UPDATE: '/reports/update'
    },
    
    // Recommendations endpoints
    RECOMMENDATIONS: {
      LIST: '/recommendations',
      DETAILS: '/recommendations/:id',
      APPLY: '/recommendations/:id/apply',
      STATUS: '/recommendations/:id/status',
      DISMISS: '/recommendations/:id/dismiss',
      HISTORY: '/recommendations/pipeline/:id/history'
    },
    
    // Decisions endpoints
    DECISIONS: {
      LIST: '/decisions',
      DETAILS: '/decisions/:id',
      MAKE: '/decisions/:id/make',
      DEFER: '/decisions/:id/defer',
      HISTORY: '/decisions/pipeline/:id/history',
      ANALYZE_IMPACT: '/decisions/:id/options/:optionId/impact'
    },

    // Settings endpoints
    SETTINGS: {
        PROFILE: '/settings/profile',
        PREFERENCES: '/settings/preferences',
        SECURITY: '/settings/security',
        NOTIFICATIONS: '/settings/notifications',
      APPEARANCE: '/settings/appearance',
      VALIDATE: '/settings/validate',
        RESET: '/settings/reset',
    },
  }
} as const;

// Helper Types
export type EndpointParams = Record<string, string>;

export interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
}

export interface ApiRequestConfig extends Omit<AxiosRequestConfig, 'url' | 'method' | 'data'> {
  routeParams?: EndpointParams;
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void;  // Changed from ProgressEvent to AxiosProgressEvent
}