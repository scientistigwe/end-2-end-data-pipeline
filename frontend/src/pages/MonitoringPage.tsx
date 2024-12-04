// src/pages/MonitoringPage.tsx
import React from 'react';
import { useMonitoring } from '../hooks/monitoring/useMonitoring';
import { MetricsCard } from '../components/monitoring/MetricsCard';
import { useSelector } from 'react-redux';
import { RootState } from '../store';

export const MonitoringPage: React.FC = () => {
  const { metrics, systemHealth, realtimeData } = useMonitoring({
    enableRealtime: true
  });

  const activePipelines = useSelector((state: RootState) =>
    state.pipelines.activePipelines
  );

  return (
    <div className="space-y-6">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Monitoring</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* System Overview */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium mb-2">System Status</h3>
            <div className={`text-2xl font-bold ${
              systemHealth.status === 'healthy' ? 'text-green-600' : 'text-red-600'
            }`}>
              {systemHealth.status}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium mb-2">Active Pipelines</h3>
            <div className="text-2xl font-bold">
              {Object.keys(activePipelines).length}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium mb-2">Resource Usage</h3>
            <div className="text-2xl font-bold">
              {metrics?.resourceUsage || '0%'}
            </div>
          </div>
        </section>

        {/* Real-time Metrics */}
        <section>
          <h2 className="text-xl font-semibold mb-4">Real-time Metrics</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(metrics || {}).map(([key, value]) => (
              <MetricsCard
                key={key}
                title={key}
                value={value}
                data={realtimeData}
              />
            ))}
          </div>
        </section>

        {/* Alerts and Notifications */}
        <section className="mt-8">
          <h2 className="text-xl font-semibold mb-4">Recent Alerts</h2>
          <div className="bg-white shadow rounded-lg divide-y divide-gray-200">
            {metrics?.alerts?.map(alert => (
              <div key={alert.id} className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-lg font-medium">{alert.title}</h4>
                    <p className="text-sm text-gray-500">{alert.message}</p>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-sm ${
                    alert.severity === 'high'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {alert.severity}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
};
