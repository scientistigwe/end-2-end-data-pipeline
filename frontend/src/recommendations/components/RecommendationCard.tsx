import React from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/common/components/ui/card";
import { Badge } from "@/common/components/ui/badge";
import { Button } from "@/common/components/ui/button";
import { ChevronRight, CheckCircle, Clock, AlertCircle } from "lucide-react";
import {
  RECOMMENDATION_TYPE_LABELS,
  RECOMMENDATION_STATUS_LABELS,
} from "../constants";
import { IMPACT_LEVEL_LABELS } from "@/common/types/common";
import type { Recommendation } from "../types/events";

interface RecommendationCardProps {
  recommendation: Recommendation;
  onSelect?: (recommendation: Recommendation) => void;
  className?: string;
}

export const RecommendationCard: React.FC<RecommendationCardProps> = ({
  recommendation,
  onSelect,
  className = "",
}) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "in_progress":
        return <Clock className="h-4 w-4 text-blue-500" />;
      case "pending":
        return <AlertCircle className="h-4 w-4 text-orange-500" />;
      default:
        return null;
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case "high":
        return "bg-red-100 text-red-800";
      case "medium":
        return "bg-yellow-100 text-yellow-800";
      case "low":
        return "bg-blue-100 text-blue-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <Card className={`hover:shadow-md transition-shadow ${className}`}>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="space-y-1">
          <CardTitle className="text-base font-semibold line-clamp-2">
            {recommendation.title}
          </CardTitle>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary" className="text-xs">
              {RECOMMENDATION_TYPE_LABELS[recommendation.type]}
            </Badge>
            <Badge
              variant="secondary"
              className={`text-xs ${getImpactColor(recommendation.impact)}`}
            >
              {IMPACT_LEVEL_LABELS[recommendation.impact]}
            </Badge>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {getStatusIcon(recommendation.status)}
          <Badge variant="outline" className="text-xs">
            {RECOMMENDATION_STATUS_LABELS[recommendation.status]}
          </Badge>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground line-clamp-2">
            {recommendation.description}
          </p>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Confidence:</span>
              <Badge variant="secondary" className="text-xs">
                {recommendation.confidence}%
              </Badge>
            </div>

            {onSelect && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onSelect(recommendation)}
                className="text-sm"
              >
                View Details
                <ChevronRight className="ml-2 h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
