// src/report/api/config.ts
export const API_CONFIG = {
    BASE_PATH: '/api/v1/reports',
    ENDPOINTS: {
      LIST: '/',
      CREATE: '/',
      GET: '/:id',
      DELETE: '/:id',
      STATUS: '/:id/status',
      EXPORT: '/:id/export',
      SCHEDULE: '/schedule',
      METADATA: '/:id/metadata',
      PREVIEW: '/:id/preview',
      TEMPLATES: '/templates'
    },
    TIMEOUT: 30000,
    MAX_RETRIES: 3
  } as const;
  
