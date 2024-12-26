// src/decisions/providers/DecisionProvider.tsx
import React, { createContext, useCallback, useState, useMemo } from "react";
import { useDispatch } from "react-redux";
import { DecisionService } from "../services/decisionService";
import { handleApiError } from "../../common/utils/api/apiUtils";
import {
  setError as setGlobalError,
  setLoading,
} from "../store/decisionsSlice";
import { DECISION_MESSAGES } from "../constants";
import type { Decision, DecisionFilters, DecisionVote } from "../types/base";

interface DecisionContextType {
  // State
  decisions: Decision[];
  selectedDecision: Decision | null;
  filters: DecisionFilters;
  isLoading: boolean;
  error: Error | null;

  // Decision Actions
  loadDecisions: (
    pipelineId: string,
    filters?: DecisionFilters
  ) => Promise<void>;
  makeDecision: (
    decisionId: string,
    optionId: string,
    comment?: string
  ) => Promise<void>;
  deferDecision: (
    decisionId: string,
    reason: string,
    deferUntil: string
  ) => Promise<void>;
  addVote: (
    decisionId: string,
    vote: DecisionVote,
    comment?: string
  ) => Promise<void>;

  // UI Actions
  setFilters: (filters: DecisionFilters) => void;
  selectDecision: (decision: Decision | null) => void;
  clearError: () => void;
}

export const DecisionContext = createContext<DecisionContextType | undefined>(
  undefined
);

interface DecisionProviderProps {
  children: React.ReactNode;
}

export const DecisionsProvider: React.FC<DecisionProviderProps> = ({
  children,
}) => {
  const dispatch = useDispatch();

  // State
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [selectedDecision, setSelectedDecision] = useState<Decision | null>(
    null
  );
  const [filters, setFilters] = useState<DecisionFilters>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setErrorState] = useState<Error | null>(null);

  // Error Handling
  const handleError = useCallback(
    (err: unknown, fallbackMessage: string) => {
      handleApiError(err);
      const errorMessage = err instanceof Error ? err.message : fallbackMessage;
      setErrorState(new Error(errorMessage));
      dispatch(setGlobalError(errorMessage));
    },
    [dispatch]
  );

  const clearError = useCallback(() => {
    setErrorState(null);
    dispatch(setGlobalError(null));
  }, [dispatch]);

  // Decision Actions
  const loadDecisions = useCallback(
    async (pipelineId: string, filters?: DecisionFilters) => {
      dispatch(setLoading(true));
      setIsLoading(true);
      try {
        const data = await DecisionService.listDecisions(pipelineId, filters);
        setDecisions(data);
        clearError();
      } catch (err) {
        handleError(err, DECISION_MESSAGES.ERRORS.LOAD_FAILED);
      } finally {
        dispatch(setLoading(false));
        setIsLoading(false);
      }
    },
    [dispatch, handleError, clearError]
  );

  const makeDecision = useCallback(
    async (decisionId: string, optionId: string, comment?: string) => {
      dispatch(setLoading(true));
      setIsLoading(true);
      try {
        const updatedDecision = await DecisionService.makeDecision(
          decisionId,
          optionId,
          comment
        );
        setDecisions((prev) =>
          prev.map((d) => (d.id === decisionId ? updatedDecision : d))
        );
        clearError();
      } catch (err) {
        handleError(err, DECISION_MESSAGES.ERRORS.MAKE_FAILED);
      } finally {
        dispatch(setLoading(false));
        setIsLoading(false);
      }
    },
    [dispatch, handleError, clearError]
  );

  const deferDecision = useCallback(
    async (decisionId: string, reason: string, deferUntil: string) => {
      dispatch(setLoading(true));
      setIsLoading(true);
      try {
        const updatedDecision = await DecisionService.deferDecision(
          decisionId,
          reason,
          deferUntil
        );
        setDecisions((prev) =>
          prev.map((d) => (d.id === decisionId ? updatedDecision : d))
        );
        clearError();
      } catch (err) {
        handleError(err, DECISION_MESSAGES.ERRORS.DEFER_FAILED);
      } finally {
        dispatch(setLoading(false));
        setIsLoading(false);
      }
    },
    [dispatch, handleError, clearError]
  );

  const addVote = useCallback(
    async (decisionId: string, vote: DecisionVote, comment?: string) => {
      dispatch(setLoading(true));
      setIsLoading(true);
      try {
        await DecisionService.addVote(decisionId, vote, comment);
        const pipelineId = decisions[0]?.pipelineId;
        if (pipelineId) {
          await loadDecisions(pipelineId);
        }
        clearError();
      } catch (err) {
        handleError(err, DECISION_MESSAGES.ERRORS.VOTE_FAILED);
      } finally {
        dispatch(setLoading(false));
        setIsLoading(false);
      }
    },
    [dispatch, decisions, loadDecisions, handleError, clearError]
  );

  // Context value
  const value = useMemo(
    () => ({
      // State
      decisions,
      selectedDecision,
      filters,
      isLoading,
      error,

      // Decision Actions
      loadDecisions,
      makeDecision,
      deferDecision,
      addVote,

      // UI Actions
      setFilters,
      selectDecision: setSelectedDecision,
      clearError,
    }),
    [
      decisions,
      selectedDecision,
      filters,
      isLoading,
      error,
      loadDecisions,
      makeDecision,
      deferDecision,
      addVote,
      clearError,
    ]
  );

  return (
    <DecisionContext.Provider value={value}>
      {children}
    </DecisionContext.Provider>
  );
};
