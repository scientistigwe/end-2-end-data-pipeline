// src/decisions/pages/DecisionsPage.tsx
import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useDecisions } from '../hooks/useDecisions';
import { DecisionCard } from '../components/DecisionCard';
import { DecisionFilters } from '../components/DecisionFilters';
import { DecisionStats } from '../components/DecisionStats';
import { useModal } from '../../common/hooks/useModal';
import { Alert, AlertTitle, AlertDescription } from '../../common/components/ui/alert';
import { Loader } from '../../common/components/feedback/Loader';
import { Button } from '../../common/components/ui/button';
import { RefreshCw } from 'lucide-react';

export const DecisionsPage: React.FC = () => {
  const { pipelineId } = useParams<{ pipelineId: string }>();
  const decisionModal = useModal({
    id: 'decision-modal',
    onOpen: () => {
      // Handle modal open
    },
    onClose: () => {
      // Handle modal close
    }
  });
  
  const {
    decisions,
    makeDecision,
    deferDecision,
    isLoading,
    error,
    refreshDecisions
  } = useDecisions(pipelineId!);

  useEffect(() => {
    refreshDecisions();
  }, [pipelineId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader text="Loading decisions..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertTitle>Error Loading Decisions</AlertTitle>
          <AlertDescription>
            {error.message}
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={() => refreshDecisions()}
            >
              Try Again
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const hasDecisions = decisions && decisions.length > 0;

  return (
    <div className="space-y-6 p-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Decisions</h1>
        <Button 
          onClick={() => refreshDecisions()}
          variant="outline"
          className="gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      <DecisionStats decisions={decisions || []} />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <DecisionFilters
            filters={{}}
            onFilterChange={() => {}}
            onReset={() => {}}
          />
        </div>

        <div className="lg:col-span-3">
          {hasDecisions ? (
            <div className="space-y-4">
              {decisions.map((decision) => (
                <DecisionCard
                  key={decision.id}
                  decision={decision}
                  onView={() => decisionModal.open({ decision })}
                  onMake={() => makeDecision(decision.id, '', '')}
                  onDefer={() => deferDecision(decision.id, '', '')}
                />
              ))}
            </div>
          ) : (
            <Alert variant="info" className="mt-4">
              <AlertTitle>No Decisions Found</AlertTitle>
              <AlertDescription>
                There are currently no decisions available for this pipeline.
                {pipelineId && (
                  <div className="mt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => refreshDecisions()}
                    >
                      Refresh Data
                    </Button>
                  </div>
                )}
              </AlertDescription>
            </Alert>
          )}
        </div>
      </div>
    </div>
  );
};

export default DecisionsPage;