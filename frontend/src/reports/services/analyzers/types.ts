// src/report/services/analyzers/types.ts
import type { Report, ReportMetric, ReportMetadata } from '../../types/report';

export interface MetricAnalyzer {
  analyze(report: Report): ReportMetric[];
  generateSummary(metrics: ReportMetric[]): string;
  generateMetadata(report: Report): ReportMetadata;
}


