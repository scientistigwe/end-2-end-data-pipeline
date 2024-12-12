  // src/report/api/index.ts
  export { API_CONFIG } from './config';
  export { ApiClient } from './client';
  export { ReportsApi } from './reportsApi';
  
  // Create and export singleton instance
  export const reportsApi = new ReportsApi();