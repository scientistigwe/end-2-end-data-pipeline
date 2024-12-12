// src/report/context/ReportContext.tsx
import React, { createContext, useContext } from 'react';
import type {
  Report,
  ReportConfig,
  ReportStatus,
  ReportMetadata,
  ScheduleConfig,
  ExportOptions
} from '../types/report';

interface ReportContextValue {
  // Report State
  selectedReportId: string | null;
  setSelectedReportId: (id: string | null) => void;

  // Report Operations
  createReport: (config: ReportConfig) => Promise<Report>;
  updateReport: (id: string, updates: Partial<ReportConfig>) => Promise<Report>;
  deleteReport: (id: string) => Promise<void>;
  
  // Report Generation
  generateReport: (id: string) => Promise<void>;
  cancelGeneration: (id: string) => Promise<void>;
  getReportStatus: (id: string) => Promise<ReportStatus>;
  
  // Report Export
  exportReport: (id: string, options: ExportOptions) => Promise<string>;
  
  // Report Scheduling
  scheduleReport: (config: ScheduleConfig) => Promise<void>;
  updateSchedule: (id: string, updates: Partial<ScheduleConfig>) => Promise<void>;
  
  // Report Metadata
  getReportMetadata: (id: string) => Promise<ReportMetadata>;
  
  // Loading States
  isLoading: boolean;
  error: string | null;
}

const ReportContext = createContext<ReportContextValue | undefined>(undefined);

export function useReportContext() {
  const context = useContext(ReportContext);
  if (context === undefined) {
    throw new Error('useReportContext must be used within a ReportProvider');
  }
  return context;
}

export { ReportContext };

