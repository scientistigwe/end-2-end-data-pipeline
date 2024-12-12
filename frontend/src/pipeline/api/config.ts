// src/pipeline/api/config.ts
export const API_CONFIG = {
    BASE_PATH: '/api/v1/pipelines',
    ENDPOINTS: {
      LIST: '/',
      CREATE: '/',
      GET: '/:id',
      UPDATE: '/:id',
      DELETE: '/:id',
      START: '/:id/start',
      STOP: '/:id/stop',
      PAUSE: '/:id/pause',
      RESUME: '/:id/resume',
      RETRY: '/:id/retry',
      LOGS: '/:id/logs',
      METRICS: '/:id/metrics',
      RUNS: '/:id/runs',
      VALIDATE: '/validate'
    },
    TIMEOUT: 30000,
    RETRY_COUNT: 3
  } as const;
  

