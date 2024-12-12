// src/report/services/reportService.ts
import type {
  Report,
  ReportConfig,
  ReportMetadata,
  ScheduleConfig,
  ReportType
} from '../types/report';
import { REPORT_CONSTANTS } from '../constants';
import { QualityAnalyzer } from './analyzers/qualityAnalyzer';
import { PerformanceAnalyzer } from './analyzers/performanceAnalyzer';
import { InsightAnalyzer } from './analyzers/insightAnalyzer';
import { SummaryAnalyzer } from './analyzers/summaryAnalyzer';
import type { MetricAnalyzer } from './analyzers/types';

class ReportService {
  private analyzers: Record<ReportType, MetricAnalyzer>;

  constructor() {
    this.analyzers = {
      quality: new QualityAnalyzer(),
      performance: new PerformanceAnalyzer(),
      insight: new InsightAnalyzer(),
      summary: new SummaryAnalyzer()
    };
  }

  validateReportConfig(config: ReportConfig): {
    isValid: boolean;
    errors: string[];
  } {
    const errors: string[] = [];

    // Validate required fields
    if (!config.name || config.name.length < REPORT_CONSTANTS.VALIDATION.NAME_MIN_LENGTH) {
      errors.push(`Name must be at least ${REPORT_CONSTANTS.VALIDATION.NAME_MIN_LENGTH} characters`);
    }

    if (config.name.length > REPORT_CONSTANTS.VALIDATION.NAME_MAX_LENGTH) {
      errors.push(`Name must not exceed ${REPORT_CONSTANTS.VALIDATION.NAME_MAX_LENGTH} characters`);
    }

    if (!config.pipelineId) {
      errors.push('Pipeline ID is required');
    }

    // Validate time range if provided
    if (config.timeRange) {
      const start = new Date(config.timeRange.start);
      const end = new Date(config.timeRange.end);
      
      if (isNaN(start.getTime())) {
        errors.push('Invalid start date');
      }
      if (isNaN(end.getTime())) {
        errors.push('Invalid end date');
      }
      if (start > end) {
        errors.push('Start date must be before end date');
      }
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  validateScheduleConfig(config: ScheduleConfig): {
    isValid: boolean;
    errors: string[];
  } {
    const errors: string[] = [];

    // First validate the base report config
    const baseValidation = this.validateReportConfig(config);
    errors.push(...baseValidation.errors);

    // Validate schedule-specific fields
    if (!config.frequency) {
      errors.push('Schedule frequency is required');
    }

    // Validate recipients
    if (!config.recipients || config.recipients.length === 0) {
      errors.push('At least one recipient is required');
    }

    if (config.recipients && config.recipients.length > REPORT_CONSTANTS.VALIDATION.MAX_RECIPIENTS) {
      errors.push(`Maximum ${REPORT_CONSTANTS.VALIDATION.MAX_RECIPIENTS} recipients allowed`);
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    config.recipients?.forEach(email => {
      if (!emailRegex.test(email)) {
        errors.push(`Invalid email format: ${email}`);
      }
    });

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  analyzeReportData(report: Report): ReportMetadata {
    const analyzer = this.analyzers[report.config.type];
    if (!analyzer) {
      throw new Error(`Unsupported report type: ${report.config.type}`);
    }

    return analyzer.generateMetadata(report);
  }
}

export const reportService = new ReportService();