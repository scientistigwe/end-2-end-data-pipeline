// src/components/decisions/DecisionCard.tsx
import React from "react";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "../../common/components/ui/card";
import { Button } from "../../common/components/ui/button";
import { Badge } from "../../common/components/ui/badge";
import { Alert } from "../../common/components/ui/alert";
import { Clock, AlertTriangle } from "lucide-react";
import type { Decision } from "../types/decisions";

interface DecisionCardProps {
  decision: Decision;
  onView: (id: string) => void;
  onMake: (id: string) => void;
  onDefer: (id: string) => void;
  className?: string;
}

export const DecisionCard: React.FC<DecisionCardProps> = ({
  decision,
  onView,
  onMake,
  onDefer,
  className = "",
}) => {
  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
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

  const isExpiringSoon =
    decision.deadline &&
    new Date(decision.deadline).getTime() - new Date().getTime() <
      24 * 60 * 60 * 1000;

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <Badge className={getUrgencyColor(decision.urgency)}>
              {decision.type}
            </Badge>
            <h3 className="text-lg font-medium mt-2">{decision.title}</h3>
          </div>
          <Badge variant="outline">{decision.status}</Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <p className="text-gray-600">{decision.description}</p>

        {decision.deadline && (
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-gray-500" />
            <span className="text-sm text-gray-500">
              Deadline: {new Date(decision.deadline).toLocaleString()}
            </span>
          </div>
        )}

        {isExpiringSoon && (
          <Alert variant="warning">
            <AlertTriangle className="h-4 w-4" />
            <span className="ml-2">
              This decision requires immediate attention!
            </span>
          </Alert>
        )}

        <div className="grid grid-cols-2 gap-4">
          {decision.options.map((option) => (
            <div key={option.id} className="p-3 border rounded-lg">
              <h4 className="font-medium">{option.title}</h4>
              <p className="text-sm text-gray-600 mt-1">{option.description}</p>
              <Badge className="mt-2" variant="outline">
                Impact: {option.impact}
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>

      <CardFooter className="justify-between">
        <div className="text-sm text-gray-500">
          Created by: {decision.createdBy}
        </div>
        <div className="space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onDefer(decision.id)}
          >
            Defer
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onView(decision.id)}
          >
            View Details
          </Button>
          <Button
            size="sm"
            onClick={() => onMake(decision.id)}
            disabled={decision.status !== "pending"}
          >
            Make Decision
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
};
