  // src/pipeline/api/index.ts
  export { API_CONFIG } from './config';
  export { ApiClient } from './client';
  export { PipelineApi } from './pipelineApi';
  
  // Create and export a singleton instance
  export const pipelineApi = new PipelineApi();