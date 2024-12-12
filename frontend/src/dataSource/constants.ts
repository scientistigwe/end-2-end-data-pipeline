// src/dataSource/constants.ts
export const DATASOURCE_CONFIG = {
    REFRESH_INTERVAL: 30000,
    PREVIEW_LIMIT: 100,
    CONNECTION_TIMEOUT: 30000,
    MAX_FILE_SIZE: 100 * 1024 * 1024, // 100MB
    MAX_BATCH_SIZE: 1000,
  } as const;
  
  export const DATASOURCE_MESSAGES = {
    ERRORS: {
      LOAD_FAILED: 'Failed to load data sources',
      FETCH_FAILED: 'Failed to fetch data source details',
      CREATE_FAILED: 'Failed to create data source',
      UPDATE_FAILED: 'Failed to update data source',
      DELETE_FAILED: 'Failed to delete data source',
      VALIDATION_FAILED: 'Validation failed',
      PREVIEW_FAILED: 'Failed to preview data',
      UPLOAD_FAILED: 'Failed to upload file',
      DB_CONNECTION_FAILED: 'Failed to connect to database',
      API_CONNECTION_FAILED: 'Failed to connect to API',
      S3_CONNECTION_FAILED: 'Failed to connect to S3',
      STREAM_CONNECTION_FAILED: 'Failed to connect to stream',
      DISCONNECT_FAILED: 'Failed to disconnect source',
      SCHEMA_FETCH_FAILED: 'Failed to fetch database schema',
      QUERY_FAILED: 'Query execution failed',
      BUCKET_INFO_FAILED: 'Failed to fetch bucket information',
      DOWNLOAD_FAILED: 'Failed to download object',
      METRICS_FETCH_FAILED: 'Failed to fetch metrics'
    },
    SUCCESS: {
      CREATED: 'Data source created successfully',
      UPDATED: 'Data source updated successfully',
      DELETED: 'Data source deleted successfully',
      VALIDATED: 'Validation completed successfully',
      CONNECTED: 'Connection established successfully',
      DISCONNECTED: 'Disconnected successfully'
    }
  } as const;
  
  
