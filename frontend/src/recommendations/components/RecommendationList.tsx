import React from 'react';
import { RecommendationCard } from './RecommendationCard';
import { Alert } from '@/common/components/ui/alert';
import type { Recommendation } from '../types/recommendations';

interface RecommendationListProps {
  recommendations: Recommendation[];
  onSelect?: (recommendation: Recommendation) => void;
  className?: string;
}

export const RecommendationList: React.FC<RecommendationListProps> = ({
  recommendations,
  onSelect,
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
          onSelect={onSelect}
          className="w-full"
        />
      ))}
    </div>
  );
};