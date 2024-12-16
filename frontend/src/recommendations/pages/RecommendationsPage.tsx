// src/recommendations/pages/RecommendationsPage.tsx
import React, { useEffect } from "react";
import { useParams } from "react-router-dom";
import { RecommendationList } from "../components/RecommendationList";
import { RecommendationFilters } from "../components/RecommendationFilter";
import { useRecommendations } from "../hooks/useRecommendations";
import {
  Alert,
  AlertTitle,
  AlertDescription,
} from "../../common/components/ui/alert";
import { Loader } from "../../common/components/feedback/Loader";
import { Button } from "../../common/components/ui/button";
import { RefreshCw } from "lucide-react";

const RecommendationsPage: React.FC = () => {
  const { pipelineId } = useParams<{ pipelineId: string }>();
  const {
    recommendations,
    isLoading,
    error,
    applyRecommendation,
    dismissRecommendation,
    refreshRecommendations,
  } = useRecommendations(pipelineId!);

  useEffect(() => {
    refreshRecommendations();
  }, [pipelineId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader text="Loading recommendations..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertTitle>Error Loading Recommendations</AlertTitle>
          <AlertDescription>
            {error.message}
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={() => refreshRecommendations()}
            >
              Try Again
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Recommendations</h1>
        <Button
          onClick={() => refreshRecommendations()}
          variant="outline"
          className="gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <RecommendationFilters
            filters={{}}
            onChange={() => {}}
            onReset={() => {}}
          />
        </div>

        <div className="lg:col-span-3">
          <RecommendationList
            recommendations={recommendations || []}
            onApply={applyRecommendation}
            onDismiss={dismissRecommendation}
          />
        </div>
      </div>
    </div>
  );
};

export default RecommendationsPage;
