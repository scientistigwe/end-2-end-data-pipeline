// src/hooks/analysis/useQualityAnalysis.ts
// src/hooks/analysis/useQualityAnalysis.ts
import { useState, useCallback } from 'react';
import { useQuery, useMutation } from 'react-query';
import { analysisApi } from '../../services/api/analysisAPI';
import { handleApiError } from '../../utils/helpers/apiUtils';
import type { 
  ApiResponse,
  AnalysisResult,
  QualityConfig,
  QualityReport,
  QualityIssuesSummary,
} from '../../services/api/types';
import { QualityAnalysisHookResult, FixMutationPayload } from './types';

export const useQualityAnalysis = (pipelineId: string): QualityAnalysisHookResult => {
  const [analysisId, setAnalysisId] = useState<string | null>(null);

  const startAnalysisMutation = useMutation<
    ApiResponse<{ analysisId: string }>,
    Error,
    Omit<QualityConfig, 'type' | 'pipelineId'>
  >(
    (config = {}) => {
      return analysisApi.startQualityAnalysis({
        type: 'quality',
        pipelineId,
        ...config
      });
    },
    {
      onSuccess: (response) => {
        if (response.data?.analysisId) {
          setAnalysisId(response.data.analysisId);
        }
      },
      onError: handleApiError
    }
  );

  const statusQuery = useQuery<AnalysisResult | null, Error>(
    ['qualityStatus', analysisId],
    async () => {
      if (!analysisId) return null;
      const response = await analysisApi.getQualityStatus(analysisId);
      return response.data ?? null;
    },
    {
      enabled: !!analysisId,
      refetchInterval: 3000
    }
  );

  const reportQuery = useQuery<QualityReport | null, Error>(
    ['qualityReport', analysisId],
    async () => {
      if (!analysisId) return null;
      const response = await analysisApi.getQualityReport(analysisId);
      return response.data ?? null;
    },
    {
      enabled: !!analysisId && statusQuery.data?.status === 'completed'
    }
  );

  const issuesSummaryQuery = useQuery<QualityIssuesSummary | null, Error>(
    ['qualityIssues', analysisId],
    async () => {
      if (!analysisId) return null;
      const response = await analysisApi.getQualityIssuesSummary(analysisId);
      return response.data ?? null;
    },
    {
      enabled: !!analysisId && statusQuery.data?.status === 'completed'
    }
  );

  const applyFixMutation = useMutation<
    ApiResponse<void>,
    Error,
    FixMutationPayload
  >(
    ({ issueId, fix }) => analysisApi.applyQualityFix(analysisId!, issueId, fix),
    {
      onError: handleApiError,
      onSuccess: () => {
        reportQuery.refetch();
        issuesSummaryQuery.refetch();
      }
    }
  );

  const cancelAnalysis = useCallback(async () => {
    if (!analysisId) return;
    
    try {
      await analysisApi.cancelQualityAnalysis(analysisId);
      setAnalysisId(null);
    } catch (error) {
      handleApiError(error);
    }
  }, [analysisId]);

  return {
    // Actions
    startAnalysis: startAnalysisMutation.mutate,
    cancelAnalysis,
    refreshStatus: statusQuery.refetch,
    refreshReport: reportQuery.refetch,
    applyFix: applyFixMutation.mutate,
    
    // State
    analysisId,
    status: statusQuery.data,
    report: reportQuery.data,
    issuesSummary: issuesSummaryQuery.data,
    
    // Status
    isStarting: startAnalysisMutation.isLoading,
    isLoading: statusQuery.isLoading || reportQuery.isLoading || issuesSummaryQuery.isLoading,
    error: statusQuery.error ?? reportQuery.error ?? issuesSummaryQuery.error ?? applyFixMutation.error ?? null
  };
};