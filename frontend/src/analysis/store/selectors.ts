// src/analysis/store/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '@/store/rootReducer';
import { AnalysisStatus, AnalysisType } from '../types/analysis';
import type { 
  AnalysisResult, 
  QualityReport, 
  InsightReport,
  Pattern,
  Anomaly, 
  Correlation
} from '../types/analysis';
import type { AnalysisState } from './analysisSlice';

// Base selectors
export const selectAnalysisState = (state: RootState): AnalysisState => 
 state.analysis;

export const selectAnalyses = (state: RootState): Record<string, AnalysisResult> => 
 state.analysis?.analyses || {};

export const selectActiveAnalyses = (state: RootState): Record<string, AnalysisResult> => 
 state.analysis?.activeAnalyses || {};

export const selectQualityReports = (state: RootState): Record<string, QualityReport> => 
 state.analysis?.qualityReports || {};

export const selectInsightReports = (state: RootState): Record<string, InsightReport> => 
 state.analysis?.insightReports || {};

export const selectSelectedAnalysisId = (state: RootState): string | null => 
 state.analysis?.selectedAnalysisId || null;

export const selectIsLoading = (state: RootState): boolean => 
 state.analysis?.isLoading || false;

export const selectError = (state: RootState): string | null => 
 state.analysis?.error || null;

// Selected item selectors
export const selectSelectedAnalysis = createSelector(
 [selectActiveAnalyses, selectSelectedAnalysisId],
 (analyses, selectedId): AnalysisResult | null => 
   selectedId ? analyses[selectedId] || null : null
);

export const selectSelectedQualityReport = createSelector(
 [selectQualityReports, selectSelectedAnalysisId],
 (reports, selectedId): QualityReport | null => 
   selectedId ? reports[selectedId] || null : null
);

export const selectSelectedInsightReport = createSelector(
 [selectInsightReports, selectSelectedAnalysisId],
 (reports, selectedId): InsightReport | null => 
   selectedId ? reports[selectedId] || null : null
);

// By ID selectors
export const selectAnalysisById = createSelector(
 [selectAnalyses, (_: RootState, id: string) => id],
 (analyses, id): AnalysisResult | null => analyses[id] || null
);

export const selectQualityReportById = createSelector(
 [selectQualityReports, (_: RootState, id: string) => id],
 (reports, id): QualityReport | null => reports[id] || null
);

export const selectInsightReportById = createSelector(
 [selectInsightReports, (_: RootState, id: string) => id],
 (reports, id): InsightReport | null => reports[id] || null
);

// Status-based selectors
export const selectPendingAnalyses = createSelector(
 [selectAnalyses],
 (analyses): AnalysisResult[] => 
   Object.values(analyses).filter(analysis => analysis.status === AnalysisStatus.PENDING)
);

export const selectRunningAnalyses = createSelector(
 [selectAnalyses],
 (analyses): AnalysisResult[] => 
   Object.values(analyses).filter(analysis => analysis.status === AnalysisStatus.RUNNING)
);

export const selectCompletedAnalyses = createSelector(
 [selectAnalyses],
 (analyses): AnalysisResult[] => 
   Object.values(analyses).filter(analysis => analysis.status === AnalysisStatus.COMPLETED)
);

export const selectFailedAnalyses = createSelector(
 [selectAnalyses],
 (analyses): AnalysisResult[] => 
   Object.values(analyses).filter(analysis => analysis.status === AnalysisStatus.FAILED)
);

export const selectCancelledAnalyses = createSelector(
 [selectAnalyses],
 (analyses): AnalysisResult[] => 
   Object.values(analyses).filter(analysis => analysis.status === AnalysisStatus.CANCELLED)
);

// Type-based selectors
export const selectQualityAnalyses = createSelector(
 [selectAnalyses],
 (analyses): AnalysisResult[] => 
   Object.values(analyses).filter(analysis => analysis.type === AnalysisType.QUALITY)
);

export const selectInsightAnalyses = createSelector(
 [selectAnalyses],
 (analyses): AnalysisResult[] => 
   Object.values(analyses).filter(analysis => analysis.type === AnalysisType.INSIGHT)
);

// Insight report detail selectors
export const selectPatternsByReportId = createSelector(
 [selectInsightReports, (_: RootState, reportId: string) => reportId],
 (reports, reportId): Pattern[] => 
   reports[reportId]?.patterns || []
);

export const selectAnomaliesByReportId = createSelector(
 [selectInsightReports, (_: RootState, reportId: string) => reportId],
 (reports, reportId): Anomaly[] => 
   reports[reportId]?.anomalies || []
);

export const selectCorrelationsByReportId = createSelector(
 [selectInsightReports, (_: RootState, reportId: string) => reportId],
 (reports, reportId): Correlation[] => 
   reports[reportId]?.correlations || []
);

// Statistics selectors
export const selectAnalysisStats = createSelector(
 [selectAnalyses],
 (analyses): {
   total: number;
   byStatus: Record<AnalysisStatus, number>;
   byType: Record<AnalysisType, number>;
 } => {
   const analysesArray = Object.values(analyses);
   
   return {
     total: analysesArray.length,
     byStatus: {
       [AnalysisStatus.PENDING]: analysesArray.filter(a => a.status === AnalysisStatus.PENDING).length,
       [AnalysisStatus.RUNNING]: analysesArray.filter(a => a.status === AnalysisStatus.RUNNING).length,
       [AnalysisStatus.COMPLETED]: analysesArray.filter(a => a.status === AnalysisStatus.COMPLETED).length,
       [AnalysisStatus.FAILED]: analysesArray.filter(a => a.status === AnalysisStatus.FAILED).length,
       [AnalysisStatus.CANCELLED]: analysesArray.filter(a => a.status === AnalysisStatus.CANCELLED).length,
     },
     byType: {
       [AnalysisType.QUALITY]: analysesArray.filter(a => a.type === AnalysisType.QUALITY).length,
       [AnalysisType.INSIGHT]: analysesArray.filter(a => a.type === AnalysisType.INSIGHT).length,
     }
   };
 }
);

// Progress selectors
export const selectOverallProgress = createSelector(
 [selectActiveAnalyses],
 (analyses): number => {
   const activeAnalyses = Object.values(analyses);
   if (activeAnalyses.length === 0) return 0;
   
   const totalProgress = activeAnalyses.reduce((sum, analysis) => sum + analysis.progress, 0);
   return Math.round(totalProgress / activeAnalyses.length);
 }
);

// Latest analyses selectors
export const selectLatestAnalyses = createSelector(
 [selectAnalyses],
 (analyses): AnalysisResult[] => 
   Object.values(analyses)
     .sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime())
     .slice(0, 5)
);