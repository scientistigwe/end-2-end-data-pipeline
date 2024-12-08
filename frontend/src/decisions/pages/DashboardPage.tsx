// src/decisions/pages/DashboardPage.tsx
import React from "react";
import { DecisionStats } from "../components/DecisionStats";
import { DecisionCard } from "../components/DecisionCard";
import { useDecisions } from "../hooks/useDecisions";
import { Card } from "../../common/components/ui/card";
import { Alert } from "../../common/components/ui/alert";
import { Loader } from "../../common/components/feedback/Loader";
import { useAuth } from "../../auth/hooks/useAuth";

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const { decisions, isLoading, error } = useDecisions(user?.id || "");

  if (isLoading) return <Loader text="Loading decisions..." />;
  if (error) return <Alert variant="destructive">{error.message}</Alert>;

  const pendingDecisions =
    decisions?.filter((d) => d.status === "pending") || [];
  const urgentDecisions = decisions?.filter((d) => d.urgency === "high") || [];

  return (
    <div className="space-y-6 p-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Decision Dashboard</h1>
      </div>

      <DecisionStats decisions={decisions || []} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <div className="flex items-center justify-between p-4 border-b">
            <h2 className="text-lg font-medium">Pending Decisions</h2>
            <span className="text-sm text-muted-foreground">
              {pendingDecisions.length} decisions
            </span>
          </div>
          <div className="p-4 space-y-4">
            {pendingDecisions.length > 0 ? (
              pendingDecisions.map((decision) => (
                <DecisionCard
                  key={decision.id}
                  decision={decision}
                  onView={() => {}}
                  onMake={() => {}}
                  onDefer={() => {}}
                />
              ))
            ) : (
              <Alert variant="info" className="my-4">
                No pending decisions found.
              </Alert>
            )}
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between p-4 border-b">
            <h2 className="text-lg font-medium">Urgent Decisions</h2>
            <span className="text-sm text-muted-foreground">
              {urgentDecisions.length} decisions
            </span>
          </div>
          <div className="p-4 space-y-4">
            {urgentDecisions.length > 0 ? (
              urgentDecisions.map((decision) => (
                <DecisionCard
                  key={decision.id}
                  decision={decision}
                  onView={() => {}}
                  onMake={() => {}}
                  onDefer={() => {}}
                />
              ))
            ) : (
              <Alert variant="info" className="my-4">
                No urgent decisions found.
              </Alert>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};