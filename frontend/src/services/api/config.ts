// src/services/api/config.ts

// In your API_CONFIG
export const API_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_URL || '/api/v1',
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
      VERIFY_EMAIL: '/auth/verify-email'
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
      DISCONNECT: '/sources/:id/disconnect',
      STATUS: '/sources/:id/status',
      API: {
        CONNECT: '/sources/api/connect',
        STATUS: '/sources/api/status',
        METADATA: '/sources/api/metadata',
        TEST: '/sources/api/:id/test',

      },
      DATABASE: {
        QUERY: '/sources/database/query',
        METADATA: '/sources/database/metadata',
        CONNECT: '/sources/database/connect',
        TEST: '/sources/database/:id/test',
        STATUS: '/sources/database/:id/status'
      },
      S3: {
        METADATA: '/sources/s3/metadata',
        CONNECT: '/sources/s3/connect',
        LIST: '/sources/s3/:id/list',
        STATUS: '/sources/s3/:id/status'

      },
      STREAM: {
        START: '/sources/stream/start',
        STOP: '/sources/stream/stop',
        METADATA: '/sources/stream/metadata',
        CONNECT: '/sources/stream/connect',
        STATUS: '/sources/stream/:id/status'
      },      
      FILE: {
        UPLOAD: '/sources/file/upload',
        METADATA: '/sources/file/:id/metadata'
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
      LOGS: '/pipelines/:id/logs'
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
      SCHEDULE: '/reports/schedule'
    },
    
    // Recommendations endpoints
    RECOMMENDATIONS: {
      LIST: '/recommendations/pipeline/:id',
      DETAILS: '/recommendations/:id',
      APPLY: '/recommendations/:id/apply',
      STATUS: '/recommendations/:id/status',
      DISMISS: '/recommendations/:id/dismiss',
      HISTORY: '/recommendations/pipeline/:id/history'
    },
    
    // Decisions endpoints
    DECISIONS: {
      LIST: '/decisions/pipeline/:id',
      DETAILS: '/decisions/:id',
      MAKE: '/decisions/:id/make',
      DEFER: '/decisions/:id/defer',
      HISTORY: '/decisions/pipeline/:id/history',
      ANALYZE_IMPACT: '/decisions/:id/options/:optionId/impact'
    },
  }
} as const;

export const formatEndpoint = (endpoint: string, params: Record<string, string>): string => {
  let formattedEndpoint = endpoint;
  Object.entries(params).forEach(([key, value]) => {
    formattedEndpoint = formattedEndpoint.replace(`:${key}`, value);
  });
  return formattedEndpoint;
};

// Helper type for endpoint parameters
export type EndpointParams = Record<string, string>;