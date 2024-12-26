  // src/report/utils/dataTransforms.ts
  import type { Report, ReportMetric } from '../types/models';
  
  export function transformMetricsForChart(metrics: ReportMetric[]): {
    labels: string[];
    values: number[];
    colors: string[];
  } {
    return {
      labels: metrics.map(m => m.name),
      values: metrics.map(m => m.value),
      colors: metrics.map(m => getMetricStatusColor(m.status))
    };
  }
  
  export function groupReportsByType(reports: Report[]): Record<ReportType, Report[]> {
    return reports.reduce((acc, report) => {
      const type = report.config.type;
      if (!acc[type]) {
        acc[type] = [];
      }
      acc[type].push(report);
      return acc;
    }, {} as Record<ReportType, Report[]>);
  }
  
  export function filterReportsByDateRange(
    reports: Report[],
    start: Date,
    end: Date
  ): Report[] {
    return reports.filter(report => {
      const reportDate = new Date(report.createdAt);
      return reportDate >= start && reportDate <= end;
    });
  }
  