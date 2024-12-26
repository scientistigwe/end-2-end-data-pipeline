// src/decisions/hooks/useDecisionImpact.ts
import { useState } from 'react';
import { decisionsApi } from '../api/decisionsApi';
import { handleApiError } from '../../common/utils/api/apiUtils';
import type { DecisionImpactAnalysis } from '../types/base';

export const useDecisionImpact = () => {
  const [impact, setImpact] = useState<DecisionImpactAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const analyzeImpact = async (decisionId: string, optionId: string) => {
    setIsLoading(true);
    try {
      const response = await decisionsApi.analyzeImpact(decisionId, optionId);
      setImpact(response.data);
      setError(null);
      return response.data;
    } catch (err) {
      handleApiError(err);
      setImpact(null);
      const errorMessage = new Error('Failed to analyze impact');
      setError(errorMessage);
      throw errorMessage;
    } finally {
      setIsLoading(false);
    }
  };

  return { impact, isLoading, error, analyzeImpact };
};