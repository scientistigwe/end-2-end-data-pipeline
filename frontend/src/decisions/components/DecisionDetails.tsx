// src/components/decisions/DecisionDetails.tsx
import React, { useState } from "react";
import { Card, CardHeader, CardContent } from "../../common/components/ui/card";
import { Button } from "../../common/components/ui/button";
import { Badge } from "../../common/components/ui/badge";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../../common/components/ui/tabs";
import type { DecisionDetails as DecisionDetailsType } from "../types/base";

interface DecisionDetailsProps {
  details: DecisionDetailsType;
  onVote: (vote: "approve" | "reject" | "defer") => void;
  onComment: (content: string) => void;
  className?: string;
}

export const DecisionDetails: React.FC<DecisionDetailsProps> = ({
  details,
  onVote,
  onComment,
  className = "",
}) => {
  const [newComment, setNewComment] = useState("");

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <Badge>{details.type}</Badge>
            <h2 className="text-2xl font-bold mt-2">{details.title}</h2>
          </div>
          <Badge variant="outline" className="text-lg">
            {details.status}
          </Badge>
        </div>
      </CardHeader>

      <CardContent>
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="analysis">Analysis</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
            <TabsTrigger value="discussion">Discussion</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="prose max-w-none">
              <p>{details.description}</p>
              <h3>Options</h3>
              <div className="grid grid-cols-1 gap-4">
                {details.options.map((option) => (
                  <div key={option.id} className="border rounded-lg p-4">
                    <h4 className="font-medium">{option.title}</h4>
                    <p className="mt-2">{option.description}</p>
                    <div className="mt-4 space-y-2">
                      <Badge variant="outline">Impact: {option.impact}</Badge>
                      {option.consequences.length > 0 && (
                        <div>
                          <h5 className="text-sm font-medium">Consequences:</h5>
                          <ul className="list-disc list-inside">
                            {option.consequences.map((consequence, index) => (
                              <li key={index} className="text-sm">
                                {consequence}
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
          </TabsContent>

          <TabsContent value="analysis">
            {details.analysis && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium mb-2">Risks</h3>
                  <ul className="list-disc list-inside space-y-2">
                    {details.analysis.risks.map((risk, index) => (
                      <li key={index}>{risk}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="text-lg font-medium mb-2">Benefits</h3>
                  <ul className="list-disc list-inside space-y-2">
                    {details.analysis.benefits.map((benefit, index) => (
                      <li key={index}>{benefit}</li>
                    ))}
                  </ul>
                </div>
                {details.analysis.alternatives && (
                  <div>
                    <h3 className="text-lg font-medium mb-2">Alternatives</h3>
                    <ul className="list-disc list-inside space-y-2">
                      {details.analysis.alternatives.map(
                        (alternative, index) => (
                          <li key={index}>{alternative}</li>
                        )
                      )}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </TabsContent>

          <TabsContent value="history">
            <div className="space-y-4">
              {details.history.map((entry) => (
                <div
                  key={entry.id}
                  className="border-l-4 border-gray-200 pl-4 py-2"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <Badge>{entry.action}</Badge>
                      <span className="ml-2 text-sm text-gray-600">
                        by {entry.user}
                      </span>
                    </div>
                    <span className="text-sm text-gray-500">
                      {new Date(entry.timestamp).toLocaleString()}
                    </span>
                  </div>
                  {entry.changes && entry.changes.length > 0 && (
                    <div className="mt-2 text-sm">
                      <h4 className="font-medium">Changes:</h4>
                      <ul className="list-disc list-inside">
                        {entry.changes.map((change, index) => (
                          <li key={index}>
                            {change.field}: {String(change.oldValue)} →{" "}
                            {String(change.newValue)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="discussion">
            <div className="space-y-6">
              <div className="space-y-4">
                {details.comments?.map((comment) => (
                  <div key={comment.id} className="p-4 bg-gray-50 rounded-lg">
                    <div className="flex justify-between">
                      <span className="font-medium">{comment.user}</span>
                      <span className="text-sm text-gray-500">
                        {new Date(comment.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="mt-2">{comment.content}</p>
                  </div>
                ))}
              </div>

              <div className="mt-4">
                <textarea
                  className="w-full p-2 border rounded-lg"
                  rows={3}
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Add your comment..."
                />
                <Button
                  className="mt-2"
                  onClick={() => {
                    onComment(newComment);
                    setNewComment("");
                  }}
                  disabled={!newComment.trim()}
                >
                  Add Comment
                </Button>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <div className="mt-6 flex justify-end space-x-2">
          <Button variant="outline" onClick={() => onVote("defer")}>
            Defer
          </Button>
          <Button variant="destructive" onClick={() => onVote("reject")}>
            Reject
          </Button>
          <Button variant="default" onClick={() => onVote("approve")}>
            Approve
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
