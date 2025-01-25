// src/insight/hooks/useAnalysis.ts
import { useCallback, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { 
  setAnalysis, 
  setQualityReport, 
  setInsightReport, 
  setLoading, 
  setError,
  updateAnalysisProgress 
} from '../store/analysisSlice';
import { 
  selectSelectedAnalysis,
  selectSelectedQualityReport,
  selectSelectedInsightReport 
} from '../store/selectors';
import { analysisApi } from '../api/analysisApi';
import type { 
  QualityConfig, 
  InsightConfig, 
  ExportOptions,
  AnalysisResult,
  QualityReport,
  InsightReport 
} from '../types/insight';

export const useAnalysis = () => {
  const dispatch = useDispatch();
  const selectedAnalysis = useSelector(selectSelectedAnalysis);
  const selectedQualityReport = useSelector(selectSelectedQualityReport);
  const selectedInsightReport = useSelector(selectSelectedInsightReport);

  // Quality Analysis Methods
  const startQualityAnalysis = useCallback(async (config: QualityConfig) => {
    try {
      dispatch(setLoading(true));
      dispatch(setError(null));
      const response = await analysisApi.startQualityAnalysis(config);
      dispatch(setAnalysis(response.data));
      return response.data;
    } catch (error) {
      dispatch(setError(error instanceof Error ? error.message : 'Failed to start quality analysis'));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const getQualityReport = useCallback(async (analysisId: string) => {
    try {
      dispatch(setLoading(true));
      const response = await analysisApi.getQualityReport(analysisId);
      dispatch(setQualityReport({ id: analysisId, report: response.data }));
      return response.data;
    } catch (error) {
      dispatch(setError(error instanceof Error ? error.message : 'Failed to fetch quality report'));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  // Insight Analysis Methods
  const startInsightAnalysis = useCallback(async (config: InsightConfig) => {
    try {
      dispatch(setLoading(true));
      dispatch(setError(null));
      const response = await analysisApi.startInsightAnalysis(config);
      dispatch(setAnalysis(response.data));
      return response.data;
    } catch (error) {
      dispatch(setError(error instanceof Error ? error.message : 'Failed to start insight analysis'));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const getInsightReport = useCallback(async (analysisId: string) => {
    try {
      dispatch(setLoading(true));
      const response = await analysisApi.getInsightReport(analysisId);
      dispatch(setInsightReport({ id: analysisId, report: response.data }));
      return response.data;
    } catch (error) {
      dispatch(setError(error instanceof Error ? error.message : 'Failed to fetch insight report'));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  // Polling for analysis status
  const pollAnalysisStatus = useCallback(async (
    analysisId: string, 
    interval: number = 5000
  ) => {
    const checkStatus = async () => {
      try {
        const response = await analysisApi.getQualityStatus(analysisId);
        dispatch(setAnalysis(response.data));
        
        if (response.data.status === 'completed') {
          return true;
        }
        return false;
      } catch (error) {
        dispatch(setError(error instanceof Error ? error.message : 'Failed to check analysis status'));
        return true; // Stop polling on error
      }
    };

    return new Promise<void>((resolve) => {
      const poll = async () => {
        const shouldStop = await checkStatus();
        if (shouldStop) {
          resolve();
        } else {
          setTimeout(poll, interval);
        }
      };
      poll();
    });
  }, [dispatch]);

  // Export Methods
  const exportReport = useCallback(async (
    analysisId: string,
    options: ExportOptions,
    type: 'quality' | 'insight'
  ) => {
    try {
      dispatch(setLoading(true));
      const response = type === 'quality' 
        ? await analysisApi.exportQualityReport(analysisId, options)
        : await analysisApi.exportInsightReport(analysisId, options);
      return response.data;
    } catch (error) {
      dispatch(setError(error instanceof Error ? error.message : 'Failed to export report'));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  return {
    // State
    selectedAnalysis,
    selectedQualityReport,
    selectedInsightReport,

    // Quality Analysis Methods
    startQualityAnalysis,
    getQualityReport,

    // Insight Analysis Methods
    startInsightAnalysis,
    getInsightReport,

    // Utility Methods
    pollAnalysisStatus,
    exportReport,
  };
};


