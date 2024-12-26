// src/recommendations/components/RecommendationHistory.tsx
import React from "react";
import { Card, CardHeader, CardContent } from "../../common/components/ui/card";
import { Badge } from "../../common/components/ui/badge";
import {
  Alert,
  AlertTitle,
  AlertDescription,
} from "../../common/components/ui/alert";
import { CheckCircle2, XCircle } from "lucide-react";
import type { RecommendationHistory as RecommendationHistoryType } from "../types/events";

interface RecommendationHistoryProps {
  history: RecommendationHistoryType[];
  className?: string;
}

export const RecommendationHistory: React.FC<RecommendationHistoryProps> = ({
  history,
  className = "",
}) => {
  if (!history.length) {
    return (
      <Alert variant="info">
        <AlertTitle>No History</AlertTitle>
        <AlertDescription>
          No recommendation actions have been taken yet.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <h3 className="text-lg font-medium">Recommendation History</h3>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {history.map((entry) => (
            <div
              key={entry.id}
              className="p-4 border rounded-lg transition-colors hover:bg-gray-50"
            >
              <div className="flex justify-between items-start">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{entry.action.type}</Badge>
                    <Badge
                      variant={
                        entry.status === "success" ? "success" : "destructive"
                      }
                    >
                      {entry.status === "success" ? (
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                      ) : (
                        <XCircle className="h-3 w-3 mr-1" />
                      )}
                      {entry.status}
                    </Badge>
                  </div>
                  <p className="text-sm">{entry.action.description}</p>
                </div>
                <time className="text-sm text-muted-foreground">
                  {new Date(entry.appliedAt).toLocaleString()}
                </time>
              </div>

              {entry.error && (
                <Alert variant="destructive" className="mt-2">
                  <AlertTitle>Error Details</AlertTitle>
                  <AlertDescription>{entry.error}</AlertDescription>
                </Alert>
              )}

              {entry.result && (
                <Alert className="mt-2">
                  <AlertTitle>Result</AlertTitle>
                  <AlertDescription>
                    Changes applied successfully
                  </AlertDescription>
                </Alert>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
