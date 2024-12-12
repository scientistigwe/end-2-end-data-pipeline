// src/monitoring/pages/MonitoringDetailsPage.tsx
import React from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardHeader, CardContent } from '../../common/components/ui/card';
import { Alert, AlertTitle, AlertDescription } from '../../common/components/ui/alert';
import { Button } from '../../common/components/ui/button';
import { Loader } from '../../common/components/feedback/Loader';
import { RefreshCw } from 'lucide-react';
import { useMonitoring } from '../hooks/useMonitoring';
import { MetricsCard } from '../components/cards/MetricsCard';
import { HealthStatusCard } from '../components/cards/HealthStatusCard';
import { ResourceUsageCard } from '../components/cards/ResourceUsageCard';
import { AlertCard } from '../components/cards/AlertCard';

export const MonitoringDetailsPage: React.FC = () => {
  const { pipelineId } = useParams<{ pipelineId: string }>();
  const {
    metrics,
    health,
    resources,
    isLoading,
    error,
    refreshAll,
    acknowledgeAlert,
    resolveAlert
  } = useMonitoring({
    pipelineId: pipelineId!
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader text="Loading monitoring data..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertTitle>Error Loading Monitoring Data</AlertTitle>
          <AlertDescription>
            {error.message}
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={() => refreshAll()}
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
        <h1 className="text-2xl font-bold">Pipeline Monitoring</h1>
        <Button 
          variant="outline" 
          onClick={() => refreshAll()}
          className="gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {health && <HealthStatusCard health={health} />}
        {resources && <ResourceUsageCard resources={resources} />}
        {metrics && (
          <MetricsCard 
            metrics={metrics}
            title="Performance Metrics"
          />
        )}
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-xl font-semibold">Active Alerts</h2>
        </CardHeader>
        <CardContent className="space-y-4">
          {health?.components.map(component => (
            component.status === 'critical' && (
              <AlertCard
                key={component.name}
                alert={{
                  id: component.name,
                  severity: 'critical',
                  message: component.message || `${component.name} is in critical state`,
                  timestamp: new Date().toISOString(),
                  metric: component.name,
                  value: 0,
                  threshold: 0,
                  resolved: false,
                  type: 'component'
                }}
                onAcknowledge={acknowledgeAlert}
                onResolve={resolveAlert}
              />
            )
          ))}
        </CardContent>
      </Card>
    </div>
  );
};

export default MonitoringDetailsPage;

