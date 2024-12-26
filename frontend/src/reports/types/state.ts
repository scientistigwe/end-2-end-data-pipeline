// src/report/types/state.ts
export interface ReportState {
    reports: Record<string, ReportStateItem>;
    activeReportId: string | null;
    isLoading: boolean;
    error: string | null;
  }
  
  export interface ReportStateItem {
    id: string;
    name: string;
    type: string;
    schedule?: ReportSchedule;
    parameters: Record<string, unknown>;
    data: Record<string, unknown>;
    metadata: ReportStateMetadata;
  }
  
  export interface ReportSchedule {
    enabled: boolean;
    frequency: 'daily' | 'weekly' | 'monthly';
    lastGenerated?: string;
    nextGeneration?: string;
  }
  
  export interface ReportStateMetadata {
    createdAt: string;
    updatedAt: string;
    generatedAt: string;
  }