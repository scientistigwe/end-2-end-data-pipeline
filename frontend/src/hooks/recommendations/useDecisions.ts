// src/hooks/decisions/useDecisions.ts
import { useState } from 'react';
import { useQuery, useMutation } from 'react-query';
import { decisionApi } from '../../services/api/decisionAPI';
import { handleApiError } from '../../utils/helpers/apiUtils';
import type {
  ApiResponse,
  Decision,
  DecisionDetails,
  DecisionHistoryEntry,
  DecisionImpactAnalysis
} from '../../services/api/types';

// Types
interface MakeDecisionParams {
  decisionId: string;
  optionId: string;
  parameters?: Record<string, unknown>;
}

interface DeferDecisionParams {
  decisionId: string;
  deferralReason: string;
  deferUntil?: string;
}

interface AnalyzeImpactParams {
  decisionId: string;
  optionId: string;
}

export interface UseDecisionsResult {
  // Actions
  makeDecision: (params: MakeDecisionParams) => void;
  deferDecision: (params: DeferDecisionParams) => void;
  analyzeImpact: (params: AnalyzeImpactParams) => void;
  refreshDecisions: () => Promise<unknown>;
  setSelectedDecision: (id: string | null) => void;

  // State
  pendingDecisions: Decision[] | null;
  decisionDetails: DecisionDetails | null;
  decisionHistory: DecisionHistoryEntry[] | null;
  selectedDecision: string | null;

  // Loading States
  isLoading: boolean;
  isDeciding: boolean;

  // Error State
  error: Error | null;
}

export const useDecisions = (pipelineId: string): UseDecisionsResult => {
  const [selectedDecision, setSelectedDecision] = useState<string | null>(null);

  // Pending Decisions Query
  const {
    data: pendingDecisions,
    error: pendingError,
    isLoading: isPendingLoading,
    refetch: refreshDecisions
  } = useQuery<Decision[], Error>(
    ['pendingDecisions', pipelineId],
    async () => {
      const response = await decisionApi.getPendingDecisions(pipelineId);
      if (!response.data) throw new Error('No decisions data received');
      return response.data;
    },
    {
      refetchInterval: 3000,
      enabled: Boolean(pipelineId)
    }
  );

  // Decision Details Query
  const {
    data: decisionDetails,
    error: detailsError,
    isLoading: isDetailsLoading
  } = useQuery<DecisionDetails | null, Error>(
    ['decisionDetails', selectedDecision],
    async () => {
      if (!selectedDecision) return null;
      const response = await decisionApi.getDecisionDetails(selectedDecision);
      if (!response.data) throw new Error('No decision details received');
      return response.data;
    },
    {
      enabled: Boolean(selectedDecision)
    }
  );

  // Decision History Query
  const {
    data: decisionHistory,
    error: historyError,
    isLoading: isHistoryLoading
  } = useQuery<DecisionHistoryEntry[], Error>(
    ['decisionHistory', pipelineId],
    async () => {
      const response = await decisionApi.getDecisionHistory(pipelineId);
      if (!response.data) throw new Error('No history data received');
      return response.data;
    },
    {
      enabled: Boolean(pipelineId)
    }
  );

  // Make Decision Mutation
  const {
    mutate: makeDecision,
    isLoading: isDeciding,
    error: makeError
  } = useMutation<ApiResponse<void>, Error, MakeDecisionParams>(
    ({ decisionId, optionId, parameters }) => 
      decisionApi.makeDecision(decisionId, optionId, parameters),
    {
      onSuccess: () => {
        refreshDecisions();
      },
      onError: handleApiError
    }
  );

  // Defer Decision Mutation
  const {
    mutate: deferDecision,
    error: deferError
  } = useMutation<ApiResponse<void>, Error, DeferDecisionParams>(
    ({ decisionId, deferralReason, deferUntil }) =>
      decisionApi.deferDecision(decisionId, deferralReason, deferUntil),
    {
      onSuccess: () => {
        refreshDecisions();
      },
      onError: handleApiError
    }
  );

  // Analyze Impact Mutation
  const {
    mutate: analyzeImpact,
    error: analyzeError
  } = useMutation<ApiResponse<DecisionImpactAnalysis>, Error, AnalyzeImpactParams>(
    ({ decisionId, optionId }) =>
      decisionApi.analyzeDecisionImpact(decisionId, optionId),
    {
      onError: handleApiError
    }
  );

  // Combine errors
  const error = pendingError || detailsError || historyError || 
                makeError || deferError || analyzeError || null;

  // Combine loading states
  const isLoading = isPendingLoading || isDetailsLoading || isHistoryLoading;

  return {
    // Actions
    makeDecision,
    deferDecision,
    analyzeImpact,
    refreshDecisions,
    setSelectedDecision,

    // State
    pendingDecisions: pendingDecisions ?? null,
    decisionDetails: decisionDetails ?? null,
    decisionHistory: decisionHistory ?? null,
    selectedDecision,

    // Loading States
    isLoading,
    isDeciding,

    // Error State
    error
  };
};
