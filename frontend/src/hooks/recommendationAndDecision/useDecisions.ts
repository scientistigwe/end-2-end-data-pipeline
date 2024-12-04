// src/hooks/decisions/useDecisions.ts
import { useState } from 'react';
import { useQuery, useMutation } from 'react-query';
import { decisionApi } from '../../services/decisionApi';
import { handleApiError } from '../../utils/apiUtils';

interface Decision {
  id: string;
  type: 'quality' | 'pipeline' | 'security';
  title: string;
  description: string;
  urgency: 'high' | 'medium' | 'low';
  options: DecisionOption[];
  context: Record<string, any>;
  deadline?: string;
}

interface DecisionOption {
  id: string;
  title: string;
  description: string;
  impact: string;
  consequences: string[];
  automaticApplicable: boolean;
}

export const useDecisions = (pipelineId: string) => {
  const [selectedDecision, setSelectedDecision] = useState<string | null>(null);

  // Get Pending Decisions
  const { data: pendingDecisions, refetch: refreshDecisions } = useQuery<Decision[]>(
    ['pendingDecisions', pipelineId],
    () => decisionApi.getPendingDecisions(pipelineId),
    {
      refetchInterval: 3000,
      enabled: !!pipelineId
    }
  );

  // Get Decision Details
  const { data: decisionDetails } = useQuery(
    ['decisionDetails', selectedDecision],
    () => decisionApi.getDecisionDetails(selectedDecision!),
    {
      enabled: !!selectedDecision
    }
  );

  // Make Decision
  const { mutate: makeDecision, isLoading: isDeciding } = useMutation(
    async ({ decisionId, optionId, parameters }: {
      decisionId: string;
      optionId: string;
      parameters?: Record<string, any>;
    }) => {
      return decisionApi.makeDecision(decisionId, optionId, parameters);
    },
    {
      onSuccess: () => {
        refreshDecisions();
      },
      onError: (error) => handleApiError(error)
    }
  );

  // Defer Decision
  const { mutate: deferDecision } = useMutation(
    async ({ decisionId, deferralReason, deferUntil }: {
      decisionId: string;
      deferralReason: string;
      deferUntil?: string;
    }) => {
      return decisionApi.deferDecision(decisionId, deferralReason, deferUntil);
    },
    {
      onSuccess: () => {
        refreshDecisions();
      }
    }
  );

  // Get Decision History
  const { data: decisionHistory } = useQuery(
    ['decisionHistory', pipelineId],
    () => decisionApi.getDecisionHistory(pipelineId),
    {
      enabled: !!pipelineId
    }
  );

  // Get Decision Impact Analysis
  const { mutate: analyzeImpact } = useMutation(
    async ({ decisionId, optionId }: { decisionId: string; optionId: string }) => {
      return decisionApi.analyzeDecisionImpact(decisionId, optionId);
    }
  );

  return {
    pendingDecisions,
    decisionDetails,
    selectedDecision,
    setSelectedDecision,
    makeDecision,
    deferDecision,
    analyzeImpact,
    refreshDecisions,
    decisionHistory,
    isDeciding
  };
};
