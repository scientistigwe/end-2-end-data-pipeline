// src/decisions/api/config.ts
export const API_CONFIG = {
    BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:3000',
    ENDPOINTS: {
      DECISIONS: {
        LIST: '/api/decisions',
        DETAILS: '/api/decisions/:id',
        MAKE: '/api/decisions/:id/make',
        DEFER: '/api/decisions/:id/defer',
        VOTE: '/api/decisions/:id/votes',
        COMMENT: '/api/decisions/:id/comments',
        HISTORY: '/api/decisions/:id/history',
        ANALYZE: '/api/decisions/:id/analyze'
      }
    },
    TIMEOUT: 30000,
    RETRY_ATTEMPTS: 3
  } as const;
  