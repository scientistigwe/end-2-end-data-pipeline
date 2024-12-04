// src/services/api/config.ts
export const API_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_URL || '/api/v1',
  TIMEOUT: 30000,
  RETRY_COUNT: 3,
  DEFAULT_HEADERS: {
    'Content-Type': 'application/json'
  },
  ENDPOINTS: {
    // Auth endpoints
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
      
      FILE: {
        UPLOAD: '/sources/file/upload',
        METADATA: '/sources/file/metadata'
      },
      API: {
        CONNECT: '/sources/api/connect',
        STATUS: '/sources/api/status'
      },
      DATABASE: {
        CONNECT: '/sources/database/connect',
        QUERY: '/sources/database/query'
      },
      S3: {
        CONNECT: '/sources/s3/connect',
        LIST: '/sources/s3/list'
      },
      STREAM: {
        CONNECT: '/sources/stream/connect',
        STATUS: '/sources/stream/status'
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
        STATUS: '/analysis/quality/:id/status',
        REPORT: '/analysis/quality/:id/report',
        EXPORT: '/analysis/quality/:id/export'
      },
      INSIGHT: {
        START: '/analysis/insight/start',
        STATUS: '/analysis/insight/:id/status',
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
      METRICS: '/monitoring/metrics',
      ALERTS: '/monitoring/alerts',
      HEALTH: '/monitoring/health'
    },

    // Reports endpoints
    REPORTS: {
      LIST: '/reports',
      CREATE: '/reports',
      GET: '/reports/:id',
      DELETE: '/reports/:id',
      EXPORT: '/reports/:id/export'
    },

    // Recommendations endpoints
    RECOMMENDATIONS: {
      LIST: '/recommendations/:pipelineId',
      APPLY: '/recommendations/apply',
      STATUS: '/recommendations/:id/status'
    }
  }
};

export const formatEndpoint = (endpoint: string, params: Record<string, string>): string => {
  let formattedEndpoint = endpoint;
  Object.entries(params).forEach(([key, value]) => {
    formattedEndpoint = formattedEndpoint.replace(`:${key}`, value);
  });
  return formattedEndpoint;
};

// Helper type for endpoint parameters
export type EndpointParams = Record<string, string>;

// Example usage:
// const endpoint = formatEndpoint(API_CONFIG.ENDPOINTS.PIPELINES.GET, { id: '123' });