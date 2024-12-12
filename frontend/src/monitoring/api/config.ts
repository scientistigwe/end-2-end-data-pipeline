// src/monitoring/api/config.ts
export const API_CONFIG = {
    BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:3000',
    TIMEOUT: 30000,
    ENDPOINTS: {
      MONITORING: {
        START: '/api/monitoring/:id/start',
        METRICS: '/api/monitoring/:id/metrics',
        HEALTH: '/api/monitoring/:id/health',
        PERFORMANCE: '/api/monitoring/:id/performance',
        ALERTS_CONFIG: '/api/monitoring/:id/alerts/config',
        ALERTS_HISTORY: '/api/monitoring/:id/alerts/history',
        RESOURCES: '/api/monitoring/:id/resources',
        TIME_SERIES: '/api/monitoring/:id/time-series',
        AGGREGATED: '/api/monitoring/:id/aggregated'
      }
    }
  } as const;
  
  