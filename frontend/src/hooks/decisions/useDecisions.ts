// src/hooks/decisions/useDecisions.ts
import { useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { decisionsApi } from '../../services/api/decisionAPI';
import { handleApiError } from '../../utils/helpers/apiUtils';
import {
  setDecisions,
  updateDecision,
  setDecisionDetails,
  setDecisionHistory,
  addHistoryEntry,
  setImpactAnalysis,
  addComment,
  setLoading,
  setError
} from '../../store/decisions/decisionsSlice';
import type { 
  DecisionFilters, 
  DecisionVote 
} from '../../types/decision';

export function useDecisions(pipelineId: string) {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  // Fetch decisions list
  const { data: decisions, refetch: refreshDecisions } = useQuery(
    ['decisions', pipelineId],
    async () => {
      dispatch(setLoading(true));
      try {
        const response = await decisionsApi.listDecisions(pipelineId);
        dispatch(setDecisions(response.data));
        return response.data;
      } catch (error) {
        handleApiError(error);
        throw error;
      } finally {
        dispatch(setLoading(false));
      }
    }
  );

  // Make decision
  const { mutate: makeDecision } = useMutation(
    async ({
      decisionId,
      optionId,
      comment
    }: {
      decisionId: string;
      optionId: string;
      comment?: string;
    }) => {
      const response = await decisionsApi.makeDecision(decisionId, optionId, comment);
      dispatch(updateDecision(response.data));
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['decisions', pipelineId]);
      },
      onError: handleApiError
    }
  );

  // Defer decision
  const { mutate: deferDecision } = useMutation(
    async ({
      decisionId,
      reason,
      deferUntil
    }: {
      decisionId: string;
      reason: string;
      deferUntil: string;
    }) => {
      const response = await decisionsApi.deferDecision(
        decisionId,
        reason,
        deferUntil
      );
      dispatch(updateDecision(response.data));
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['decisions', pipelineId]);
      },
      onError: handleApiError
    }
  );

  // Vote on decision
  const { mutate: voteOnDecision } = useMutation(
    async ({
      decisionId,
      vote,
      comment
    }: {
      decisionId: string;
      vote: DecisionVote;
      comment?: string;
    }) => {
      const response = await decisionsApi.addVote(decisionId, vote, comment);
      dispatch(addHistoryEntry({
        pipelineId,
        entry: response.data
      }));
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['decisions', pipelineId]);
      },
      onError: handleApiError
    }
  );

  // Add comment
  const { mutate: addDecisionComment } = useMutation(
    async ({
      decisionId,
      content,
      replyTo
    }: {
      decisionId: string;
      content: string;
      replyTo?: string;
    }) => {
      const response = await decisionsApi.addComment(decisionId, content, replyTo);
      dispatch(addComment({
        decisionId,
        comment: response.data
      }));
      return response.data;
    },
    {
      onError: handleApiError
    }
  );

  // Get decision details
  const getDecisionDetails = useCallback(async (decisionId: string) => {
    try {
      const response = await decisionsApi.getDecisionDetails(decisionId);
      dispatch(setDecisionDetails({
        id: decisionId,
        details: response.data
      }));
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  }, [dispatch]);

  // Analyze impact
  const analyzeImpact = useCallback(async (decisionId: string, optionId: string) => {
    try {
      const response = await decisionsApi.analyzeImpact(decisionId, optionId);
      dispatch(setImpactAnalysis({
        decisionId,
        analysis: response.data
      }));
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  }, [dispatch]);

  return {
    decisions,
    makeDecision,
    deferDecision,
    voteOnDecision,
    addDecisionComment,
    getDecisionDetails,
    analyzeImpact,
    refreshDecisions
  } as const;
}