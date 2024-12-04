// src/hooks/analysis/useInsightAnalysis.ts
import { useState, useCallback } from 'react';
import { useQuery, useMutation } from 'react-query';
import { analysisApi } from '../../services/api/analysisAPI';
import { handleApiError } from '../../utils/helpers/apiUtils';
import type { 
  AnalysisConfig, 
  BaseAnalysisOptions,
  AnalysisSeverity,
  ExportFormat,
  InsightAnalysisTypes,
  TimeRange,
  DataScope
} from './../../services/api/types';


interface InsightAnalysisOptions extends BaseAnalysisOptions {
    analysisTypes?: InsightAnalysisTypes;
    dataScope?: DataScope;
  }

interface InsightConfig extends Omit<AnalysisConfig, 'type' | 'options'> {
    type: 'insight';
    options?: InsightAnalysisOptions;
  }
  
interface Pattern {
    type: string;
    description: string;
    confidence: number;
    affectedColumns: string[];
  }
  
interface Anomaly {
    type: string;
    description: string;
    severity: AnalysisSeverity;
    timestamp: string;
  }
  
interface Correlation {
    columns: string[];
    strength: number;
    description: string;
  }
  
interface InsightReport {
    summary: {
      patternsFound: number;
      anomaliesDetected: number;
      correlationsIdentified: number;
    };
    patterns: Pattern[];
    anomalies: Anomaly[];
    correlations: Correlation[];
  }
  

/**
 * Hook for managing insight analysis operations
 * @param pipelineId - ID of the pipeline to analyze
 */
export const useInsightAnalysis = (pipelineId: string) => {
  const [analysisId, setAnalysisId] = useState<string | null>(null);

  
  const startAnalysisMutation = useMutation(
    async (config: Omit<InsightAnalysisOptions, 'pipelineId'>) => {
      const response = await analysisApi.startInsightAnalysis({
        type: 'insight',
        pipelineId,
        options: {
          ...config,
          // You can set default priority/timeout here if needed
          priority: config.priority || 'medium',
          timeout: config.timeout || 30000,
        },
      });
      return response;
    },
    {
      onSuccess: (response) => {
        setAnalysisId(response.data.analysisId);
      },
      onError: handleApiError
    }
  );


  const patternDetailsMutation = useMutation(
    (patternId: string) => analysisApi.getInsightPatternDetails(analysisId!, patternId),
    { onError: handleApiError }
  );

  const exportMutation = useMutation(
    (format: ExportFormat) => analysisApi.exportInsights(analysisId!, format),
    { onError: handleApiError }
  );

  // Queries
  const statusQuery = useQuery(
    ['insightStatus', analysisId],
    () => analysisApi.getInsightStatus(analysisId!),
    {
      enabled: !!analysisId,
      refetchInterval: 3000
    }
  );

  const reportQuery = useQuery<InsightReport>(
    ['insightReport', analysisId],
    () => analysisApi.getInsightReport(analysisId!),
    {
      enabled: !!analysisId && statusQuery.data?.status === 'completed'
    }
  );

  const trendsQuery = useQuery(
    ['insightTrends', analysisId],
    () => analysisApi.getInsightTrends(analysisId!),
    {
      enabled: !!analysisId && statusQuery.data?.status === 'completed'
    }
  );

  // Actions
  const cancelAnalysis = useCallback(async () => {
    if (analysisId) {
      try {
        await analysisApi.cancelAnalysis(analysisId, 'insight');
        setAnalysisId(null);
      } catch (error) {
        handleApiError(error);
      }
    }
  }, [analysisId]);

  return {
    // Actions
    startAnalysis: startAnalysisMutation.mutate,
    cancelAnalysis,
    refreshStatus: statusQuery.refetch,
    refreshReport: reportQuery.refetch,
    getPatternDetails: patternDetailsMutation.mutate,
    exportInsights: exportMutation.mutate,

    // State
    analysisId,
    status: statusQuery.data,
    report: reportQuery.data,
    trends: trendsQuery.data,

    // Loading states
    isStarting: startAnalysisMutation.isLoading,
    isLoading: statusQuery.isLoading || reportQuery.isLoading,
    
    // Error states
    error: statusQuery.error || reportQuery.error || trendsQuery.error
  };
};