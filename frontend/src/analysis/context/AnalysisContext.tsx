// src/analysis/context/AnalysisContext.tsx

import { createContext, useContext } from 'react';
import type {
  AnalysisResult,
  QualityConfig,
  InsightConfig,
  QualityReport,
  InsightReport,
  Pattern,
  Anomaly,
  Correlation,
  Trend
} from '../types/analysis';

interface AnalysisContextState {
  selectedAnalysis: AnalysisResult | null;
  selectedQualityReport: QualityReport | null;
  selectedInsightReport: InsightReport | null;
  isLoading: boolean;
  error: string | null;
}

interface AnalysisContextActions {
  startQualityAnalysis: (config: QualityConfig) => Promise<AnalysisResult>;
  startInsightAnalysis: (config: InsightConfig) => Promise<AnalysisResult>;
  getQualityReport: (analysisId: string) => Promise<QualityReport>;
  getInsightReport: (analysisId: string) => Promise<InsightReport>;
  getCorrelations: (analysisId: string) => Promise<Correlation[]>;
  getAnomalies: (analysisId: string) => Promise<Anomaly[]>;
  getTrends: (analysisId: string) => Promise<Trend[]>;
  getPatternDetails: (analysisId: string, patternId: string) => Promise<Pattern>;
  selectAnalysis: (analysisId: string) => void;
  pollAnalysisStatus: (analysisId: string) => Promise<void>;
  clearAnalysis: () => void;
}

export interface AnalysisContextType extends AnalysisContextState, AnalysisContextActions {}

export const AnalysisContext = createContext<AnalysisContextType | undefined>(undefined);

export const useAnalysisContext = () => {
  const context = useContext(AnalysisContext);
  if (!context) {
    throw new Error('useAnalysisContext must be used within an AnalysisProvider');
  }
  return context;
};