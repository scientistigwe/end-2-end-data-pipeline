// src/types/store.ts
import type { SystemHealth } from './monitoring';
import type { Pipeline } from './pipeline';

export interface RootState {
  pipelines: {
    activePipelines: Record<string, Pipeline>;
  };
  monitoring: {
    systemHealth: SystemHealth;
  };
}
