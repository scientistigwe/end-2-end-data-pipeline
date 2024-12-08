// src/recommendations/components/RecommendationList.tsx
import React from 'react';
import { RecommendationCard } from './RecommendationCard';
import { Alert } from '../../common/components/ui/alert';
import type { Recommendation } from '../types/recommendations';

interface RecommendationListProps {
  recommendations: Recommendation[];
  onApply: (recommendationId: string, actionId: string) => void;
  onDismiss: (recommendationId: string) => void;
  className?: string;
}

export const RecommendationList: React.FC<RecommendationListProps> = ({
  recommendations,
  onApply,
  onDismiss,
  className = ''
}) => {
  if (!recommendations.length) {
    return (
      <Alert variant="info">
        No recommendations found matching your criteria.
      </Alert>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {recommendations.map((recommendation) => (
        <RecommendationCard
          key={recommendation.id}
          recommendation={recommendation}
          onApply={(action) => onApply(recommendation.id, action.id)}
          onDismiss={() => onDismiss(recommendation.id)}
        />
      ))}
    </div>
  );
};
