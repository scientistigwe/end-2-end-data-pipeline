// src/hooks/analysis/useAnalysis.ts
import { useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { analysisApi } from '../../services/api/analysisAPI';
import { handleApiError } from '../../utils/helpers/apiUtils';
import {
  setAnalysis,
  setQualityReport,
  setInsightReport,
  setLoading,
  setError,
  
  updateAnalysisProgress
} from '../../store/analysis/analysisSlice';
import type {
  QualityConfig,
  InsightConfig,
  ExportOptions
} from '../../types/analysis';

export function useAnalysis(analysisId?: string) {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  // Quality Analysis Mutations
  const { mutate: startQualityAnalysis } = useMutation(
    (config: QualityConfig) => analysisApi.startQualityAnalysis(config),
    {
      onSuccess: (response) => {
        dispatch(setAnalysis(response.data));
        queryClient.invalidateQueries(['analysis', response.data.id]);
      },
      onError: (error) => {
        handleApiError(error);
        dispatch(setError(error.message));
      }
    }
  );

  // Insight Analysis Mutations
  const { mutate: startInsightAnalysis } = useMutation(
    (config: InsightConfig) => analysisApi.startInsightAnalysis(config),
    {
      onSuccess: (response) => {
        dispatch(setAnalysis(response.data));
        queryClient.invalidateQueries(['analysis', response.data.id]);
      },
      onError: (error) => {
        handleApiError(error);
        dispatch(setError(error.message));
      }
    }
  );

  // Analysis Status Query
  const { data: analysisStatus } = useQuery(
    ['analysis', analysisId],
    async () => {
      if (!analysisId) return null;

      const result = await (analysisId.startsWith('qa-')
        ? analysisApi.getQualityStatus(analysisId)
        : analysisApi.getInsightStatus(analysisId));

      dispatch(setAnalysis(result.data));
      
      // Update progress
      dispatch(updateAnalysisProgress({
        id: analysisId,
        progress: result.data.progress
      }));

      return result.data;
    },
    {
      enabled: !!analysisId,
      refetchInterval: (data) =>
        data?.status === 'running' ? 5000 : false
    }
  );

  // Report Queries
  const { data: qualityReport } = useQuery(
    ['quality-report', analysisId],
    async () => {
      if (!analysisId?.startsWith('qa-')) return null;
      const result = await analysisApi.getQualityReport(analysisId);
      dispatch(setQualityReport({ id: analysisId, report: result.data }));
      return result.data;
    },
    {
      enabled: !!analysisId?.startsWith('qa-') &&
        analysisStatus?.status === 'completed'
    }
  );

  const { data: insightReport } = useQuery(
    ['insight-report', analysisId],
    async () => {
      if (!analysisId?.startsWith('insight-')) return null;
      const result = await analysisApi.getInsightReport(analysisId);
      dispatch(setInsightReport({ id: analysisId, report: result.data }));
      return result.data;
    },
    {
      enabled: !!analysisId?.startsWith('insight-') &&
        analysisStatus?.status === 'completed'
    }
  );

  // Export Reports
  const { mutate: exportReport } = useMutation(
    async ({ analysisId, options }: { analysisId: string; options: ExportOptions }) => {
      if (analysisId.startsWith('qa-')) {
        return analysisApi.exportQualityReport(analysisId, options);
      } else {
        return analysisApi.exportInsightReport(analysisId, options);
      }
    },
    {
      onError: handleApiError
    }
  );

  return {
    // Actions
    startQualityAnalysis,
    startInsightAnalysis,
    exportReport,

    // Data
    analysisStatus,
    qualityReport,
    insightReport,

    // Loading States
    isLoading: analysisStatus?.status === 'running'
  } as const;
}