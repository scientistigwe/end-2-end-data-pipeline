// src/analysis/api/config.ts
export const API_CONFIG = {
    BASE_URL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000',
    TIMEOUT: 30000,
    ENDPOINTS: {
      ANALYSIS: {
        QUALITY: {
          START: 'analysis/quality/start',
          STATUS: 'analysis/quality/:id/status',
          REPORT: 'analysis/quality/:id/report',
          EXPORT: 'analysis/quality/:id/export'
        },
        INSIGHT: {
          START: 'analysis/insight/start',
          STATUS: 'analysis/insight/:id/status',
          REPORT: 'analysis/insight/:id/report',
          CORRELATIONS: 'analysis/insight/:id/correlations',
          ANOMALIES: 'analysis/insight/:id/anomalies',
          TRENDS: 'analysis/insight/:id/trends',
          PATTERN_DETAILS: 'analysis/insight/:id/patterns/:patternId',
          EXPORT: 'analysis/insight/:id/export'
        }
      }
    }
  };
  
  