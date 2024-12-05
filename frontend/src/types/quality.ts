// // src/types/quality.ts
// import { AnalysisConfig } from './analysis';

// export interface QualityConfig extends Omit<AnalysisConfig, 'type'> {
//   type: 'quality';
//   rules?: {
//     dataTypes?: boolean;
//     nullChecks?: boolean;
//     rangeValidation?: boolean;
//     customRules?: Record<string, any>;
//   };
//   thresholds?: {
//     errorThreshold?: number;
//     warningThreshold?: number;
//   };
// }

// export interface QualityReport {
//   summary: {
//     totalIssues: number;
//     criticalIssues: number;
//     warningIssues: number;
//   };
//   issues: Array<{
//     id: string;
//     type: string;
//     severity: 'critical' | 'warning' | 'info';
//     description: string;
//     affectedColumns: string[];
//     possibleFixes?: Array<{
//       id: string;
//       description: string;
//       impact: 'high' | 'medium' | 'low';
//     }>;
//   }>;
//   recommendations: Array<{
//     id: string;
//     type: string;
//     description: string;
//     impact: 'high' | 'medium' | 'low';
//   }>;
// }

// export interface QualityIssuesSummary {
//   byType: Record<string, number>;
//   bySeverity: Record<string, number>;
//   byColumn: Record<string, number>;
//   trend: {
//     lastRun: number;
//     change: number;
//   };
// }

