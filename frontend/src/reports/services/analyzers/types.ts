// src/report/pipeline/analyzers/types.ts
import type { Report, ReportMetric, ReportMetadata } from '../../types/models';

export interface MetricAnalyzer {
  analyze(report: Report): ReportMetric[];
  generateSummary(metrics: ReportMetric[]): string;
  generateMetadata(report: Report): ReportMetadata;
}


