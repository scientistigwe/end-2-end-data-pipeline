// src/hooks/monitoring/useMetricsVisualization.ts
import { useCallback } from 'react';
import { useQuery } from 'react-query';
import { monitoringApi } from '../../services/monitoringApi';

export const useMetricsVisualization = (pipelineId: string) => {
  // Get Time Series Data
  const { data: timeSeriesData } = useQuery(
    ['timeSeriesData', pipelineId],
    () => monitoringApi.getTimeSeriesData(pipelineId),
    {
      refetchInterval: 5000,
      enabled: !!pipelineId
    }
  );

  // Get Aggregated Metrics
  const { data: aggregatedMetrics } = useQuery(
    ['aggregatedMetrics', pipelineId],
    () => monitoringApi.getAggregatedMetrics(pipelineId),
    {
      enabled: !!pipelineId
    }
  );

  // Format Data for Different Chart Types
  const formatForLineChart = useCallback((data: any) => {
    // Transform data for line chart
    return data;
  }, []);

  const formatForBarChart = useCallback((data: any) => {
    // Transform data for bar chart
    return data;
  }, []);

  const formatForHeatmap = useCallback((data: any) => {
    // Transform data for heatmap
    return data;
  }, []);

  return {
    timeSeriesData,
    aggregatedMetrics,
    formatForLineChart,
    formatForBarChart,
    formatForHeatmap
  };
};