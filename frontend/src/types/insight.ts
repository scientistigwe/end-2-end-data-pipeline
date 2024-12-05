// // src/types/insight.ts
// import { TimeRange } from './common';
// import { AnalysisConfig, AnalysisSeverity } from './analysis';

// export interface InsightAnalysisTypes {
//   patterns?: boolean;
//   correlations?: boolean;
//   anomalies?: boolean;
//   trends?: boolean;
// }

// export interface DataScope {
//   columns?: string[];
//   timeRange?: TimeRange;
// }

// export interface InsightConfig extends Omit<AnalysisConfig, 'type'> {
//   type: 'insight';
//   analysisTypes?: InsightAnalysisTypes;
//   dataScope?: DataScope;
// }

// export interface InsightReport {
//   summary: {
//     patternsFound: number;
//     anomaliesDetected: number;
//     correlationsIdentified: number;
//   };
//   patterns: Array<{
//     id: string;
//     type: string;
//     description: string;
//     confidence: number;
//     affectedColumns: string[];
//   }>;
//   anomalies: Array<{
//     id: string;
//     type: string;
//     description: string;
//     severity: AnalysisSeverity;
//     timestamp: string;
//   }>;
//   correlations: Array<{
//     columns: string[];
//     strength: number;
//     description: string;
//   }>;
// }