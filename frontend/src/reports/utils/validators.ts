  // src/report/utils/validators.ts
  import { ReportConfig, ScheduleConfig } from '../types/models';
  
  export function validateTimeRange(start: Date, end: Date): boolean {
    return start < end && start >= new Date(Date.now() - 365 * 24 * 60 * 60 * 1000);
  }
  
  export function validateEmailList(emails: string[]): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emails.every(email => emailRegex.test(email));
  }
  
  export function validateReportName(name: string): boolean {
    return name.length >= REPORT_CONSTANTS.VALIDATION.NAME_MIN_LENGTH &&
           name.length <= REPORT_CONSTANTS.VALIDATION.NAME_MAX_LENGTH;
  }
