// src/pipeline/routes/utils/routeParams.ts
export function getPipelinePathWithId(path: string, id: string): string {
    return path.replace(':id', id);
  }
  
  