// src/components/recommendations/RecommendationCard.tsx
import React from "react";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, Check, X } from "lucide-react";
import type {
  Recommendation,
  RecommendationAction,
} from "../../types/recommendations";

interface RecommendationCardProps {
  recommendation: Recommendation;
  onApply: (action: RecommendationAction) => void;
  onDismiss: () => void;
  className?: string;
}

export const RecommendationCard: React.FC<RecommendationCardProps> = ({
  recommendation,
  onApply,
  onDismiss,
  className = "",
}) => {
  const getImpactColor = (impact: string) => {
    switch (impact) {
      case "high":
        return "bg-red-100 text-red-800";
      case "medium":
        return "bg-yellow-100 text-yellow-800";
      case "low":
        return "bg-green-100 text-green-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <Badge className={`mb-2 ${getImpactColor(recommendation.impact)}`}>
              {recommendation.type}
            </Badge>
            <h3 className="text-lg font-medium">{recommendation.title}</h3>
          </div>
          <Badge variant="outline">
            {recommendation.confidence.toFixed(0)}% confidence
          </Badge>
        </div>
      </CardHeader>

      <CardContent>
        <p className="text-gray-600 mb-4">{recommendation.description}</p>

        {recommendation.actions.length > 0 && (
          <div className="space-y-3">
            <h4 className="font-medium">Available Actions:</h4>
            {recommendation.actions.map((action) => (
              <div key={action.id} className="p-3 border rounded-lg">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium">{action.description}</p>
                    {action.risks && action.risks.length > 0 && (
                      <div className="mt-2">
                        <p className="text-sm text-red-600 flex items-center">
                          <AlertTriangle className="h-4 w-4 mr-1" />
                          Potential risks:
                        </p>
                        <ul className="list-disc list-inside text-sm text-red-600 ml-5">
                          {action.risks.map((risk, index) => (
                            <li key={index}>{risk}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onApply(action)}
                    disabled={!action.automaticApplicable}
                  >
                    Apply
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>

      <CardFooter className="justify-between">
        <div className="text-sm text-gray-500">
          Source: {recommendation.source}
        </div>
        <Button variant="ghost" size="sm" onClick={onDismiss}>
          <X className="h-4 w-4 mr-1" />
          Dismiss
        </Button>
      </CardFooter>
    </Card>
  );
};
