// src/pages/MonitoringPage.tsx
import React from "react";
import { useMonitoring } from "../hooks/reportAndMonitoring/useMonitoring";
import { MetricsCard } from "../components/monitoring/MetricsCard";
import { useSelector } from "react-redux";
import { RootState } from "../store";
import type {
  MetricStatus,
  Alert,
  PerformanceMetrics,
} from "../services/api/types";

interface SystemMetrics {
  resourceUsage: {
    cpu: number;
    memory: number;
    disk: number;
  };
  alerts: Alert[];
}

export const MonitoringPage: React.FC = () => {
  const {
    metrics,
    systemHealth,
    resourceUsage,
    realtimeData,
    alertHistory,
    isLoading,
    error,
  } = useMonitoring("all-pipelines");

  const activePipelines = useSelector(
    (state: RootState) => state.pipelines.activePipelines
  );

  const getStatusColor = (status: MetricStatus): string => {
    switch (status) {
      case "healthy":
        return "text-green-600";
      case "warning":
        return "text-yellow-600";
      case "critical":
        return "text-red-600";
      default:
        return "text-gray-600";
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading monitoring data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg text-red-600">
          Error loading monitoring data: {error.message}
        </div>
      </div>
    );
  }

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
            <div
              className={`text-2xl font-bold ${getStatusColor(
                systemHealth?.status ?? "critical"
              )}`}
            >
              {systemHealth?.status ?? "Unknown"}
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
              {resourceUsage ? `${resourceUsage.cpu.usage.toFixed(1)}%` : "N/A"}
            </div>
            <div className="text-sm text-gray-500">
              Memory: {resourceUsage?.memory.percentage.toFixed(1)}% | Disk:{" "}
              {resourceUsage?.disk.percentage.toFixed(1)}%
            </div>
          </div>
        </section>

        {/* Real-time Metrics */}
        <section>
          <h2 className="text-xl font-semibold mb-4">Real-time Metrics</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {metrics?.map((metric) => (
              <MetricsCard
                key={metric.timestamp}
                metricKey={String(metric.metrics.type)} // Convert to string
                currentValue={metric.metrics.value}
                status={metric.status}
                realtimeData={realtimeData}
              />
            ))}
          </div>
        </section>

        {/* Alerts and Notifications */}
        <section className="mt-8">
          <h2 className="text-xl font-semibold mb-4">Recent Alerts</h2>
          <div className="bg-white shadow rounded-lg divide-y divide-gray-200">
            {alertHistory?.map((alert) => (
              <div key={alert.id} className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-lg font-medium">{alert.metricName}</h4>
                    <p className="text-sm text-gray-500">
                      Threshold: {alert.threshold} | Value: {alert.value}
                    </p>
                  </div>
                  <span
                    className={`px-2 py-1 rounded-full text-sm ${
                      alert.severity === "critical"
                        ? "bg-red-100 text-red-800"
                        : "bg-yellow-100 text-yellow-800"
                    }`}
                  >
                    {alert.severity}
                  </span>
                </div>
              </div>
            ))}
            {!alertHistory?.length && (
              <div className="p-4 text-center text-gray-500">
                No recent alerts
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
};
