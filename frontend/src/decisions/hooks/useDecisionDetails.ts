// src/decisions/hooks/useDecisionDetails.ts
import { useState, useEffect } from 'react';
import { decisionsApi } from '../api/decisionsApi';
import { handleApiError } from '../../common/utils/api/apiUtils';
import type { DecisionDetails } from '../types/decisions';

export const useDecisionDetails = (decisionId: string | null) => {
  const [details, setDetails] = useState<DecisionDetails | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!decisionId) return;

    let mounted = true;

    const fetchDetails = async () => {
      setIsLoading(true);
      try {
        const response = await decisionsApi.getDecisionDetails(decisionId);
        if (mounted) {
          setDetails(response.data);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          handleApiError(err); // Just handle the error display
          setError(new Error('Failed to fetch decision details')); // Set a generic error
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    fetchDetails();

    return () => {
      mounted = false;
    };
  }, [decisionId]);

  return { details, isLoading, error };
};