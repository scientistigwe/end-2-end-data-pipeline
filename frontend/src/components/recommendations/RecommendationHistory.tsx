// src/components/recommendations/RecommendationHistory.tsx
import React from "react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { RecommendationHistory as RecommendationHistoryType } from "../../types/recommendations";

interface RecommendationHistoryProps {
  history: RecommendationHistoryType[];
  className?: string;
}

export const RecommendationHistory: React.FC<RecommendationHistoryProps> = ({
  history,
  className = "",
}) => {
  return (
    <Card className={className}>
      <CardHeader>
        <h3 className="text-lg font-medium">Recommendation History</h3>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {history.map((entry) => (
            <div key={entry.id} className="p-4 border rounded-lg">
              <div className="flex justify-between items-start">
                <div>
                  <Badge>{entry.action.type}</Badge>
                  <p className="mt-2">{entry.action.description}</p>
                </div>
                <Badge
                  variant={
                    entry.status === "success" ? "success" : "destructive"
                  }
                >
                  {entry.status}
                </Badge>
              </div>
              <div className="mt-2 text-sm text-gray-500">
                Applied at: {new Date(entry.appliedAt).toLocaleString()}
              </div>
              {entry.error && (
                <div className="mt-2 p-2 bg-red-50 text-red-700 rounded">
                  {entry.error}
                </div>
              )}
              {entry.result && (
                <div className="mt-2 p-2 bg-green-50 text-green-700 rounded">
                  Changes applied successfully
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
