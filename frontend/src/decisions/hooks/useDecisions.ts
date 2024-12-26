// src/decisions/hooks/useDecisions.ts
import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { DecisionService } from '../services';
import { handleApiError } from '../../common/utils/api/apiUtils';
import { DECISION_MESSAGES } from '../constants';
import {
  setDecisions,
  updateDecision,
  setDecisionDetails,
  addHistoryEntry,
  setImpactAnalysis,
  addComment,
  setLoading,
  setError
} from '../store/decisionsSlice';
import type { 
  Decision,
  DecisionDetails,
  DecisionFilters,
  DecisionVote,
} from '../types/base';

interface UseDecisionsResult {
    // Data
    decisions: Decision[] | undefined;
    selectedDecision: DecisionDetails | null;
    
    // Loading States
    isLoading: boolean;
    isDeciding: boolean;
    isDeferring: boolean;
    isVoting: boolean;
    
    // Error State
    error: Error | null;
    
    // Actions
    makeDecision: (decisionId: string, optionId: string, comment?: string) => Promise<void>;
    deferDecision: (decisionId: string, reason: string, deferUntil: string) => Promise<void>;
    voteOnDecision: (decisionId: string, vote: DecisionVote, comment?: string) => Promise<void>;
    addDecisionComment: (decisionId: string, content: string, replyTo?: string) => Promise<void>;
    getDecisionDetails: (decisionId: string) => Promise<DecisionDetails>;
    analyzeImpact: (decisionId: string, optionId: string) => Promise<void>;
    refreshDecisions: () => Promise<void>;
    setSelectedDecision: (decision: DecisionDetails | null) => void;
    applyFilters: (filters: DecisionFilters) => void;
}
  
export function useDecisions(pipelineId: string): UseDecisionsResult {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<DecisionFilters>({});
  const [selectedDecision, setSelectedDecision] = useState<DecisionDetails | null>(null);

  // Fetch decisions list - remains same
  const { 
    data: decisions, 
    isLoading,
    error: fetchError,
    refetch: refreshDecisions 
  } = useQuery(
    ['decisions', pipelineId, filters],
    async () => {
      dispatch(setLoading(true));
      try {
        const response = await DecisionService.listDecisions(pipelineId, filters);
        dispatch(setDecisions(response));
        return response;
      } catch (error) {
        handleApiError(error);
        dispatch(setError('Failed to fetch decisions'));
        throw new Error('Failed to fetch decisions');
      } finally {
        dispatch(setLoading(false));
      }
    },
    {
      refetchInterval: 30000,
      staleTime: 10000
    }
  );

  // Make decision mutation
  const { mutateAsync: makeDecision, isLoading: isDeciding } = useMutation(
    async ({ 
      decisionId, 
      optionId, 
      comment 
    }: { 
      decisionId: string; 
      optionId: string; 
      comment?: string; 
    }) => {
      try {
        const response = await DecisionService.makeDecision(decisionId, optionId, comment);
        dispatch(updateDecision(response));
        return response;
      } catch (error) {
        handleApiError(error);
        throw new Error(DECISION_MESSAGES.ERRORS.MAKE_FAILED);
      }
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['decisions', pipelineId]);
      }
    }
  );

  // Defer decision mutation
  const { mutateAsync: deferDecision, isLoading: isDeferring } = useMutation(
    async ({
      decisionId,
      reason,
      deferUntil
    }: {
      decisionId: string;
      reason: string;
      deferUntil: string;
    }) => {
      try {
        const response = await DecisionService.deferDecision(decisionId, reason, deferUntil);
        dispatch(updateDecision(response));
        return response;
      } catch (error) {
        handleApiError(error);
        throw new Error(DECISION_MESSAGES.ERRORS.DEFER_FAILED);
      }
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['decisions', pipelineId]);
      }
    }
  );

  // Vote on decision mutation
  const { mutateAsync: voteOnDecision, isLoading: isVoting } = useMutation(
    async ({
      decisionId,
      vote,
      comment
    }: {
      decisionId: string;
      vote: DecisionVote;
      comment?: string;
    }) => {
      try {
        const response = await DecisionService.addVote(decisionId, vote, comment);
        dispatch(addHistoryEntry({
          pipelineId, // Changed from decisionId to pipelineId
          entry: response
        }));
        return response;
      } catch (error) {
        handleApiError(error);
        throw new Error(DECISION_MESSAGES.ERRORS.VOTE_FAILED);
      }
    }
  );

  // Add comment mutation
  const { mutateAsync: addDecisionComment } = useMutation(
    async ({
      decisionId,
      content,
      replyTo
    }: {
      decisionId: string;
      content: string;
      replyTo?: string;
    }) => {
      try {
        const response = await DecisionService.addComment(decisionId, content, replyTo);
        dispatch(addComment({
          decisionId,
          comment: response
        }));
        return response;
      } catch (error) {
        handleApiError(error);
        throw new Error('Failed to add comment');
      }
    }
  );

  // Get decision details
  const getDecisionDetails = useCallback(async (decisionId: string) => {
    try {
      const response = await DecisionService.getDecisionDetails(decisionId);
      dispatch(setDecisionDetails({
        id: decisionId,
        details: response
      }));
      return response;
    } catch (error) {
      handleApiError(error);
      throw new Error('Failed to fetch decision details');
    }
  }, [dispatch]);


  // Apply filters
  const applyFilters = useCallback((newFilters: DecisionFilters) => {
    setFilters(newFilters);
  }, []);

  // Wrapper functions to match the interface signatures
  const handleMakeDecision = async (
    decisionId: string,
    optionId: string,
    comment?: string
  ): Promise<void> => {
    await makeDecision({ decisionId, optionId, comment });
  };

  const handleDeferDecision = async (
    decisionId: string,
    reason: string,
    deferUntil: string
  ): Promise<void> => {
    await deferDecision({ decisionId, reason, deferUntil });
  };

  const handleVoteOnDecision = async (
    decisionId: string,
    vote: DecisionVote,
    comment?: string
  ): Promise<void> => {
    await voteOnDecision({ decisionId, vote, comment });
  };

  const handleAddComment = async (
    decisionId: string,
    content: string,
    replyTo?: string
  ): Promise<void> => {
    await addDecisionComment({ decisionId, content, replyTo });
  };

  // Add wrapper for refreshDecisions
  const handleRefreshDecisions = async (): Promise<void> => {
    await refreshDecisions();
    };

 // Analyze impact mutation
 const { mutateAsync: mutateAnalyzeImpact } = useMutation(
    async ({
      decisionId,
      optionId
    }: {
      decisionId: string;
      optionId: string;
    }) => {
      try {
        const response = await DecisionService.analyzeImpact(decisionId, optionId);
        dispatch(setImpactAnalysis({
          decisionId,
          analysis: response
        }));
        return response;
      } catch (error) {
        handleApiError(error);
        throw new Error('Failed to analyze impact');
      }
    }
  );

  // Wrapper for analyzeImpact
  const handleAnalyzeImpact = async (
    decisionId: string,
    optionId: string
  ): Promise<void> => {
    await mutateAnalyzeImpact({ decisionId, optionId });
  };
   
  return {
    decisions,
    selectedDecision,
    isLoading,
    isDeciding,
    isDeferring,
    isVoting,
    error: fetchError as Error | null,
    makeDecision: handleMakeDecision,
    deferDecision: handleDeferDecision,
    voteOnDecision: handleVoteOnDecision,
    addDecisionComment: handleAddComment,
    getDecisionDetails,
    analyzeImpact: handleAnalyzeImpact,
    refreshDecisions: handleRefreshDecisions,
    setSelectedDecision,
    applyFilters
  };
}