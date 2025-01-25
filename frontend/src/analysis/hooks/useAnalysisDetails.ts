// src/insight/hooks/useAnalysisDetails.ts
import { useCallback } from 'react';
import { useDispatch } from 'react-redux';
import { setError, setLoading } from '../store/analysisSlice';
import { analysisApi } from '../api/analysisApi';
import type { Correlation, Anomaly, Pattern, Trend } from '../types/analysis';

export const useAnalysisDetails = () => {
  const dispatch = useDispatch();

  const getCorrelations = useCallback(async (analysisId: string): Promise<Correlation[]> => {
    try {
      dispatch(setLoading(true));
      const response = await analysisApi.getCorrelations(analysisId);
      return response.data;
    } catch (error) {
      dispatch(setError(error instanceof Error ? error.message : 'Failed to fetch correlations'));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const getAnomalies = useCallback(async (analysisId: string): Promise<Anomaly[]> => {
    try {
      dispatch(setLoading(true));
      const response = await analysisApi.getAnomalies(analysisId);
      return response.data;
    } catch (error) {
      dispatch(setError(error instanceof Error ? error.message : 'Failed to fetch anomalies'));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const getTrends = useCallback(async (analysisId: string): Promise<Trend[]> => {
    try {
      dispatch(setLoading(true));
      const response = await analysisApi.getTrends(analysisId);
      return response.data;
    } catch (error) {
      dispatch(setError(error instanceof Error ? error.message : 'Failed to fetch trends'));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const getPatternDetails = useCallback(async (analysisId: string, patternId: string): Promise<Pattern> => {
    try {
      dispatch(setLoading(true));
      const response = await analysisApi.getPatternDetails(analysisId, patternId);
      return response.data;
    } catch (error) {
      dispatch(setError(error instanceof Error ? error.message : 'Failed to fetch pattern details'));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  return {
    getCorrelations,
    getAnomalies,
    getTrends,
    getPatternDetails,
  };
};