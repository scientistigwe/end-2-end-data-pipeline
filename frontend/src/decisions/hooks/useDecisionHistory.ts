// src/decisions/hooks/useDecisionHistory.ts
import { useState, useEffect } from 'react';
import { decisionsApi } from '../api/decisionsApi';
import { handleApiError } from '../../common/utils/api/apiUtils';
import type { DecisionHistoryEntry } from '../types/decisions';

export const useDecisionHistory = (decisionId: string) => {
  const [history, setHistory] = useState<DecisionHistoryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const response = await decisionsApi.getDecisionHistory(decisionId);
      setHistory(response.data);
      setError(null);
    } catch (err) {
      handleApiError(err);
      setHistory([]);
      setError(new Error('Failed to fetch decision history'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let mounted = true;
    
    const loadHistory = async () => {
      setIsLoading(true);
      try {
        const response = await decisionsApi.getDecisionHistory(decisionId);
        if (mounted) {
          setHistory(response.data);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          handleApiError(err);
          setHistory([]);
          setError(new Error('Failed to fetch decision history'));
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    loadHistory();

    return () => {
      mounted = false;
    };
  }, [decisionId]);

  return { history, isLoading, error, refreshHistory: fetchHistory };
};

