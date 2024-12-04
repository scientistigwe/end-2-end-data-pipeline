// src/hooks/analysis/useQualityAnalysis.ts
import { useState, useCallback } from 'react';
import { useQuery, useMutation } from 'react-query';
import { analysisApi, QualityConfig } from '../../services/api/analysisAPI';
import { handleApiError } from '../../utils/helpers/apiUtils';


interface QualityReport {
  summary: {
    totalIssues: number;
    criticalIssues: number;
    warningIssues: number;
  };
  issues: Array<{
    id: string;
    type: string;
    severity: 'critical' | 'warning' | 'info';
    description: string;
    affectedColumns: string[];
    possibleFixes?: Array<{
      id: string;
      description: string;
      impact: 'high' | 'medium' | 'low';
    }>;
  }>;
  recommendations: Array<{
    id: string;
    type: string;
    description: string;
    impact: 'high' | 'medium' | 'low';
  }>;
}

interface QualityIssuesSummary {
  byType: Record<string, number>;
  bySeverity: Record<string, number>;
  byColumn: Record<string, number>;
  trend: {
    lastRun: number;
    change: number;
  };
}

interface FixPayload {
  issueId: string;
  fix: {
    type: string;
    parameters?: Record<string, any>;
  };
}

export const useQualityAnalysis = (pipelineId: string) => {
  const [analysisId, setAnalysisId] = useState<string | null>(null);

  // Start Quality Analysis
  const { mutate: startAnalysis, isLoading: isStarting } = useMutation(
    async (config: Omit<QualityConfig, 'type' | 'pipelineId'>) => {
      const response = await analysisApi.startQualityAnalysis({
        type: 'quality',
        pipelineId,
        ...config
      });
      setAnalysisId(response.data.analysisId);
      return response;
    },
    {
      onError: handleApiError
    }
  );

  // Get Analysis Status
  const { data: status, refetch: refreshStatus } = useQuery(
    ['qualityStatus', analysisId],
    () => analysisApi.getQualityStatus(analysisId!),
    {
      enabled: !!analysisId,
      refetchInterval: 3000
    }
  );

  // Get Quality Report
  const { data: report, refetch: refreshReport } = useQuery<QualityReport>(
    ['qualityReport', analysisId],
    () => analysisApi.getQualityReport(analysisId!),
    {
      enabled: !!analysisId && status?.status === 'completed'
    }
  );

  // Cancel Analysis
  const cancelAnalysis = useCallback(async () => {
    if (analysisId) {
      await analysisApi.cancelQualityAnalysis(analysisId);
      setAnalysisId(null);
    }
  }, [analysisId]);

  // Get Issues Summary
  const { data: issuesSummary } = useQuery<QualityIssuesSummary>(
    ['qualityIssues', analysisId],
    () => analysisApi.getQualityIssuesSummary(analysisId!),
    {
      enabled: !!analysisId && status?.status === 'completed'
    }
  );

  // Apply Fix
  const { mutate: applyFix } = useMutation(
    ({ issueId, fix }: FixPayload) => 
      analysisApi.applyQualityFix(analysisId!, issueId, fix),
    {
      onError: handleApiError,
      onSuccess: () => {
        // Refetch report and summary after applying fix
        refreshReport();
        refreshStatus();
      }
    }
  );

  return {
    startAnalysis,
    cancelAnalysis,
    refreshStatus,
    refreshReport,
    applyFix,
    analysisId,
    status,
    report,
    issuesSummary,
    isStarting
  };
};

