// src/report/constants.ts
export const REPORT_CONSTANTS = {
    TYPES: {
      QUALITY: 'quality',
      INSIGHT: 'insight',
      PERFORMANCE: 'performance',
      SUMMARY: 'summary'
    } as const,
  
    FORMATS: {
      PDF: 'pdf',
      CSV: 'csv',
      JSON: 'json'
    } as const,
  
    STATUS: {
      PENDING: 'pending',
      GENERATING: 'generating',
      COMPLETED: 'completed',
      FAILED: 'failed'
    } as const,
  
    FREQUENCIES: {
      DAILY: 'daily',
      WEEKLY: 'weekly',
      MONTHLY: 'monthly'
    } as const,
  
    PRIORITIES: {
      HIGH: 'high',
      NORMAL: 'normal',
      LOW: 'low'
    } as const,
  
    METRIC_STATUS: {
      HEALTHY: 'healthy',
      WARNING: 'warning',
      CRITICAL: 'critical'
    } as const,
  
    VALIDATION: {
      NAME_MIN_LENGTH: 3,
      NAME_MAX_LENGTH: 50,
      DESCRIPTION_MAX_LENGTH: 200,
      MAX_RECIPIENTS: 10
    },
  
    TIME_RANGES: {
      LAST_24_HOURS: '24h',
      LAST_7_DAYS: '7d',
      LAST_30_DAYS: '30d',
      CUSTOM: 'custom'
    },
  
    DEFAULTS: {
      FORMAT: 'pdf',
      PRIORITY: 'normal',
      PAGE_SIZE: 20
    },
  
    UI: {
      REPORT_LIST_PAGE_SIZE: 10,
      METRIC_CHART_HEIGHT: 300,
      REFRESH_INTERVAL: 30000 // 30 seconds
    }
  } as const;
  
  // Type guards
  export function isReportType(type: string): type is ReportType {
    return Object.values(REPORT_CONSTANTS.TYPES).includes(type as ReportType);
  }
  
  export function isReportFormat(format: string): format is ReportFormat {
    return Object.values(REPORT_CONSTANTS.FORMATS).includes(format as ReportFormat);
  }
  
  export function isReportStatus(status: string): status is ReportStatus {
    return Object.values(REPORT_CONSTANTS.STATUS).includes(status as ReportStatus);
  }
  
  export function isReportFrequency(frequency: string): frequency is ReportScheduleFrequency {
    return Object.values(REPORT_CONSTANTS.FREQUENCIES).includes(frequency as ReportScheduleFrequency);
  }