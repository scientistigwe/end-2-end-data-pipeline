// src/dataSource/api/config.ts
export const API_CONFIG = {
    BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:3000',
    TIMEOUT: 30000,
    ENDPOINTS: {
      DATA_SOURCES: {
        LIST: '/api/data-sources',
        GET: '/api/data-sources/:id',
        CREATE: '/api/data-sources',
        UPDATE: '/api/data-sources/:id',
        DELETE: '/api/data-sources/:id',
        VALIDATE: '/api/data-sources/:id/validate',
        PREVIEW: '/api/data-sources/:id/preview',
        SYNC: '/api/data-sources/:id/sync',
        
        // File operations
        FILE: {
          UPLOAD: '/api/data-sources/file/upload',
          PARSE: '/api/data-sources/file/:fileId/parse'
        },
  
        // Database operations
        DATABASE: {
          CONNECT: '/api/data-sources/database/connect',
          SCHEMA: '/api/data-sources/:id/schema',
          QUERY: '/api/data-sources/:id/query',
          TEST: '/api/data-sources/:id/test'
        },
  
        // API operations
        API: {
          CONNECT: '/api/data-sources/api/connect',
          TEST: '/api/data-sources/api/test',
          EXECUTE: '/api/data-sources/:id/execute'
        },
  
        // S3 operations
        S3: {
          CONNECT: '/api/data-sources/s3/connect',
          LIST: '/api/data-sources/:id/list',
          INFO: '/api/data-sources/:id/info',
          DOWNLOAD: '/api/data-sources/:id/download'
        },
  
        // Stream operations
        STREAM: {
          CONNECT: '/api/data-sources/stream/connect',
          STATUS: '/api/data-sources/:id/status',
          METRICS: '/api/data-sources/:id/metrics'
        },
  
        // Common operations
        STATUS: '/api/data-sources/:id/status',
        DISCONNECT: '/api/data-sources/:id/disconnect'
      }
    }
  } as const;
  