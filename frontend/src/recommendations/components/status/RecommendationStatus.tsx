// src/recommendations/components/status/RecommendationStatus.tsx
import React from 'react';
import { Badge } from '@/common/components/ui/badge';
import type { RecommendationStatus } from '../../types/recommendations';

interface RecommendationStatusBadgeProps {
  status: RecommendationStatus;
  className?: string;
}

export const RecommendationStatusBadge: React.FC<RecommendationStatusBadgeProps> = ({
  status,
  className = ''
}) => {
  const getStatusColor = (status: RecommendationStatus): string => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'applied':
        return 'bg-green-100 text-green-800';
      case 'dismissed':
        return 'bg-gray-100 text-gray-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Badge className={`${getStatusColor(status)} ${className}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
};
