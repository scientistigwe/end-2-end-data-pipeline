// src/pages/DashboardPage.tsx
import React from 'react';
import { useSelector } from 'react-redux';
import { PipelineCard } from '../components/pipeline/PipelineCard';
import { MetricsCard } from '../components/monitoring/MetricsCard';
import { useMonitoring } from '../hooks/monitoring/useMonitoring';
import { RootState } from '../store';

export const DashboardPage: React.FC = () => {
  const activePipelines = useSelector((state: RootState) =>
    Object.values(state.pipelines.activePipelines)
  );
  const systemHealth = useSelector((state: RootState) =>
    state.monitoring.systemHealth
  );

  const { metrics } = useMonitoring({});

  return (
    <div className="space-y-6">
      {/* Overview Section */}
      <section>
        <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium">Active Pipelines</h3>
            <p className="text-3xl font-bold">{activePipelines.length}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium">System Health</h3>
            <p className={`text-3xl font-bold ${
              systemHealth.status === 'healthy' ? 'text-green-600' : 'text-red-600'
            }`}>
              {systemHealth.status}
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium">Total Processes</h3>
            <p className="text-3xl font-bold">{metrics?.totalProcesses || 0}</p>
          </div>
        </div>
      </section>

      {/* Active Pipelines Section */}
      <section>
        <h2 className="text-xl font-semibold mb-4">Active Pipelines</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {activePipelines.map(pipeline => (
            <PipelineCard key={pipeline.id} pipelineId={pipeline.id} />
          ))}
        </div>
      </section>

      {/* Metrics Overview */}
      <section>
        <h2 className="text-xl font-semibold mb-4">Key Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {activePipelines.map(pipeline => (
            <MetricsCard
              key={pipeline.id}
              pipelineId={pipeline.id}
              metricKey="performance"
            />
          ))}
        </div>
      </section>
    </div>
  );
};
