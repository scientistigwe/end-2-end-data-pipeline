// src/report/types/events.ts
import type { ReportMetadata } from './models';
import { REPORT_EVENTS } from './base';

export interface ReportError extends Error {
  name: 'ReportError';
  code?: string;
  timestamp: string;
  component: 'report';
  details: {
    reportId?: string;
    [key: string]: unknown;
  };
}

export interface ReportGenerationCompleteDetail {
  reportId: string;
  status: string;
  metadata: ReportMetadata;
}

export interface ReportExportReadyDetail {
  exports: Array<{
    id: string;
    downloadUrl: string;
  }>;
}

export interface ReportStatusChangeDetail {
  reportId: string;
  status: string;
  previousStatus?: string;
  progress?: number;
}

export interface ReportErrorDetail {
  error: string;
  code?: string;
  reportId?: string;
}

export type ReportEventMap = {
  [REPORT_EVENTS.GENERATION_COMPLETE]: CustomEvent<ReportGenerationCompleteDetail>;
  [REPORT_EVENTS.EXPORT_READY]: CustomEvent<ReportExportReadyDetail>;
  [REPORT_EVENTS.STATUS_CHANGE]: CustomEvent<ReportStatusChangeDetail>;
  [REPORT_EVENTS.ERROR]: CustomEvent<ReportErrorDetail>;
};

export type ReportEventName = keyof ReportEventMap;