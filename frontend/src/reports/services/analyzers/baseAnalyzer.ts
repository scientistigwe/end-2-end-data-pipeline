// src/report/services/analyzers/baseAnalyzer.ts
import type { Report, ReportMetric, ReportMetadata } from '../../types/report';
import type { MetricAnalyzer } from './types';

export abstract class BaseAnalyzer implements MetricAnalyzer {
  abstract analyze(report: Report): ReportMetric[];
  abstract generateSummary(metrics: ReportMetric[]): string;

  generateMetadata(report: Report): ReportMetadata {
    const metrics = this.analyze(report);
    return {
      totalCount: metrics.length,
      metrics,
      summary: this.generateSummary(metrics)
    };
  }
}

