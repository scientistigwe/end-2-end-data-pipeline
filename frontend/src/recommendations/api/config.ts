// src/recommendations/api/config.ts
export const API_CONFIG = {
    BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:3000',
    ENDPOINTS: {
      RECOMMENDATIONS: {
        LIST: '/api/recommendations',
        DETAILS: '/api/recommendations/:id',
        APPLY: '/api/recommendations/:id/apply',
        DISMISS: '/api/recommendations/:id/dismiss',
        STATUS: '/api/recommendations/:id/status',
        HISTORY: '/api/recommendations/:id/history'
      }
    },
    TIMEOUT: 30000
  } as const;
  