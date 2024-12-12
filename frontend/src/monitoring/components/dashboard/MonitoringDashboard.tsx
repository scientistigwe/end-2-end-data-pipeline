
// src/monitoring/components/dashboard/MonitoringDashboard.tsx
import React from 'react';
import { useMonitoring } from '../../hooks/useMonitoring';
import { Alert, AlertTitle, AlertDescription } from '../../../common/components/ui/alert';
import { Loader } from '../../../common/components/feedback/Loader';
import { MetricsCard } from '../cards/MetricsCard';
import { HealthStatusCard } from '../health/HealthStatusCard';
import { ResourceUsageCard } from '../resources/ResourceUsageCard';
import { MetricsTable } from '../tables/MetricsTable';
import { MetricsFilter } from '../filters/MetricsFilter';
import { ExportMetricsButton } from '../buttons/ExportMetricsButton';
import { AlertCard } from '../alerts/AlertCard';

interface MonitoringDashboardProps {
  pipelineId: string;
  className?: string;
}

export const MonitoringDashboard: React.FC<MonitoringDashboardProps> = ({
  pipelineId,
  className = ''
}) => {
  const {
    metrics,
    health,
    resources,
    isLoading,
    error,
    refreshAll
  } = useMonitoring({ pipelineId });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader text="Loading monitoring data..." />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>
          {error.message}
          <Button
            variant="outline"
            size="sm"
            onClick={refreshAll}
            className="mt-2"
          >
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Monitoring Dashboard</h2>
        <ExportMetricsButton metrics={metrics || []} />
      </div>

      <MetricsFilter 
        onFilterChange={() => {}}
        className="mt-4"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {health && <HealthStatusCard health={health} />}
        {resources && <ResourceUsageCard resources={resources} />}
        {metrics?.map((metric, index) => (
          <MetricsCard
            key={index}
            title={metric.type}
            value={Object.values(metric.values)[0]}
            status={metric.status}
            className="h-full"
          />
        ))}
      </div>

      {metrics && (
        <MetricsTable 
          metrics={metrics}
          className="mt-6"
        />
      )}
    </div>
  );
};