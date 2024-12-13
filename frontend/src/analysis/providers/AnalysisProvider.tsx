// src/analysis/providers/AnalysisProvider.tsx

import React, { useCallback, useEffect, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { AnalysisContext } from '../context/AnalysisContext';
import { analysisService } from '../services/analysisService';
import { 
  setAnalysis, 
  setQualityReport, 
  setInsightReport,
  setSelectedAnalysis,
  setLoading,
  setError,
  updateAnalysisProgress
} from '../store/analysisSlice';
import {
  selectSelectedAnalysis,
  selectSelectedQualityReport,
  selectSelectedInsightReport
} from '../store/selectors';
import type { 
  AnalysisResult,
  QualityConfig,
  InsightConfig
} from '../types/analysis';

export const AnalysisProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const dispatch = useDispatch();
  const selectedAnalysis = useSelector(selectSelectedAnalysis);
  const selectedQualityReport = useSelector(selectSelectedQualityReport);
  const selectedInsightReport = useSelector(selectSelectedInsightReport);

  const startQualityAnalysis = useCallback(async (config: QualityConfig) => {
    dispatch(setLoading(true));
    try {
      const result = await analysisService.startQualityAnalysis(config);
      dispatch(setAnalysis(result));
      return result;
    } catch (error) {
      dispatch(setError((error as Error).message));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const startInsightAnalysis = useCallback(async (config: InsightConfig) => {
    dispatch(setLoading(true));
    try {
      const result = await analysisService.startInsightAnalysis(config);
      dispatch(setAnalysis(result));
      return result;
    } catch (error) {
      dispatch(setError((error as Error).message));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const pollAnalysisStatus = useCallback(async (analysisId: string) => {
    const poll = async () => {
      try {
        const status = await analysisService.getAnalysisStatus(analysisId);
        dispatch(setAnalysis(status));
        dispatch(updateAnalysisProgress({ 
          id: analysisId, 
          progress: status.progress 
        }));

        if (status.status === 'completed' || status.status === 'failed') {
          return status;
        }

        await new Promise(resolve => setTimeout(resolve, 2000));
        return poll();
      } catch (error) {
        dispatch(setError((error as Error).message));
        throw error;
      }
    };

    return poll();
  }, [dispatch]);

  const getQualityReport = useCallback(async (analysisId: string) => {
    try {
      const report = await analysisService.getQualityReport(analysisId);
      dispatch(setQualityReport({ id: analysisId, report }));
      return report;
    } catch (error) {
      dispatch(setError((error as Error).message));
      throw error;
    }
  }, [dispatch]);

  const getInsightReport = useCallback(async (analysisId: string) => {
    try {
      const report = await analysisService.getInsightReport(analysisId);
      dispatch(setInsightReport({ id: analysisId, report }));
      return report;
    } catch (error) {
      dispatch(setError((error as Error).message));
      throw error;
    }
  }, [dispatch]);

  // Additional methods for getting detailed analysis results
  const getCorrelations = useCallback(
    (analysisId: string) => analysisService.getCorrelations(analysisId),
    []
  );

  const getAnomalies = useCallback(
    (analysisId: string) => analysisService.getAnomalies(analysisId),
    []
  );

  const getTrends = useCallback(
    (analysisId: string) => analysisService.getTrends(analysisId),
    []
  );

  const getPatternDetails = useCallback(
    (analysisId: string, patternId: string) => 
      analysisService.getPatternDetails(analysisId, patternId),
    []
  );

  const selectAnalysis = useCallback((analysisId: string) => {
    dispatch(setSelectedAnalysis(analysisId));
  }, [dispatch]);

  const clearAnalysis = useCallback(() => {
    dispatch(setSelectedAnalysis(null));
  }, [dispatch]);

  const value = useMemo(() => ({
    // State
    selectedAnalysis,
    selectedQualityReport,
    selectedInsightReport,
    isLoading: false,
    error: null,

    // Actions
    startQualityAnalysis,
    startInsightAnalysis,
    getQualityReport,
    getInsightReport,
    getCorrelations,
    getAnomalies,
    getTrends,
    getPatternDetails,
    selectAnalysis,
    pollAnalysisStatus,
    clearAnalysis
  }), [
    selectedAnalysis,
    selectedQualityReport,
    selectedInsightReport,
    startQualityAnalysis,
    startInsightAnalysis,
    getQualityReport,
    getInsightReport,
    getCorrelations,
    getAnomalies,
    getTrends,
    getPatternDetails,
    selectAnalysis,
    pollAnalysisStatus,
    clearAnalysis
  ]);

  return (
    <AnalysisContext.Provider value={value}>
      {children}
    </AnalysisContext.Provider>
  );
};