// src/components/decisions/DecisionTimeline.tsx
import React from "react";
import { Card } from "../../common/components/ui/card";
import type { DecisionHistoryEntry } from "../types/decisions";

interface DecisionTimelineProps {
  history: DecisionHistoryEntry[];
  className?: string;
}

export const DecisionTimeline: React.FC<DecisionTimelineProps> = ({
  history,
  className = "",
}) => {
  return (
    <Card className={`p-4 ${className}`}>
      <h3 className="font-medium mb-4">Decision Timeline</h3>
      <div className="relative">
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />
        <div className="space-y-6">
          {history.map((entry) => (
            <div key={entry.id} className="relative pl-8">
              <div className="absolute left-2 top-2 w-4 h-4 rounded-full border-2 border-blue-500 bg-white" />
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <p className="font-medium">{entry.action}</p>
                    <p className="text-sm text-gray-600">by {entry.user}</p>
                  </div>
                  <span className="text-sm text-gray-500">
                    {new Date(entry.timestamp).toLocaleString()}
                  </span>
                </div>
                {entry.changes && entry.changes.length > 0 && (
                  <div className="mt-2 text-sm">
                    <p className="font-medium">Changes:</p>
                    <ul className="list-disc list-inside mt-1">
                      {entry.changes.map((change, index) => (
                        <li key={index}>
                          {change.field}:{" "}
                          <span className="text-gray-500">
                            {String(change.oldValue)}
                          </span>
                          {" → "}
                          <span className="text-gray-900">
                            {String(change.newValue)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
};
