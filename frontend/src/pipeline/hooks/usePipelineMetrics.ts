// src/pipeline/hooks/usePipelineMetrics.ts
import { useQuery } from 'react-query';
import { useDispatch } from 'react-redux';
import { PipelineApi } from '../api/pipelineApi';
import { setPipelineMetrics } from '../store/pipelineSlice';
import { PIPELINE_CONSTANTS } from '../constants';
import type { PipelineMetrics } from '../types/pipeline';

interface UsePipelineMetricsOptions {
  timeRange?: {
    start: string;
    end: string;
  };
}

export function usePipelineMetrics(
  pipelineId?: string,
  options?: UsePipelineMetricsOptions
) {
  const dispatch = useDispatch();
  const pipelineApi = new PipelineApi();

  const { data, isLoading, error, refetch } = useQuery<PipelineMetrics[]>(
    ['pipelineMetrics', pipelineId, options?.timeRange],
    async () => {
      try {
        if (pipelineId) {
          // Single pipeline metrics
          const response = await pipelineApi.getPipelineMetrics(
            pipelineId, 
            options?.timeRange
          );
          
          const formattedMetrics = response.map(metric => ({
            ...metric,
            timestamp: new Date(metric.timestamp).toISOString(),
            metrics: {
              ...metric.metrics,
              throughput: Number(metric.metrics.throughput),
              latency: Number(metric.metrics.latency),
              errorRate: Number(metric.metrics.errorRate)
            }
          }));

          dispatch(setPipelineMetrics({ pipelineId, metrics: formattedMetrics }));
          return formattedMetrics;
        } else {
          // Global metrics
          const pipelines = await pipelineApi.listPipelines();
          const metricsPromises = pipelines.map(pipeline => 
            pipelineApi.getPipelineMetrics(pipeline.id, options?.timeRange)
              .then(metrics => ({
                pipelineId: pipeline.id,
                metrics
              }))
              .catch(() => ({ pipelineId: pipeline.id, metrics: [] }))
          );
          
          const allMetricsResults = await Promise.all(metricsPromises);
          
          // Dispatch individual pipeline metrics
          allMetricsResults.forEach(({ pipelineId: id, metrics }) => {
            if (metrics.length > 0) {
              const formattedMetrics = metrics.map(metric => ({
                ...metric,
                timestamp: new Date(metric.timestamp).toISOString(),
                metrics: {
                  ...metric.metrics,
                  throughput: Number(metric.metrics.throughput),
                  latency: Number(metric.metrics.latency),
                  errorRate: Number(metric.metrics.errorRate)
                }
              }));
              
              dispatch(setPipelineMetrics({ pipelineId: id, metrics: formattedMetrics }));
            }
          });

          // Return aggregated metrics for the chart
          return allMetricsResults
            .flatMap(({ metrics }) => metrics)
            .map(metric => ({
              ...metric,
              timestamp: new Date(metric.timestamp).toISOString(),
              metrics: {
                ...metric.metrics,
                throughput: Number(metric.metrics.throughput),
                latency: Number(metric.metrics.latency),
                errorRate: Number(metric.metrics.errorRate)
              }
            }))
            .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
        }
      } catch (error) {
        console.error('Error fetching pipeline metrics:', error);
        throw error;
      }
    },
    {
      refetchInterval: PIPELINE_CONSTANTS.METRICS.REFRESH_INTERVAL,
      enabled: true,
      staleTime: PIPELINE_CONSTANTS.METRICS.REFRESH_INTERVAL - 1000,
      retry: 3,
      onError: (error) => {
        console.error('Error in metrics query:', error);
      }
    }
  );

  const refresh = async () => {
    try {
      await refetch();
    } catch (error) {
      console.error('Error refreshing metrics:', error);
    }
  };

  return {
    metrics: data || [],
    isLoading,
    error,
    refresh,
    isEmpty: !data || data.length === 0,
    hasError: !!error
  } as const;
}

export type UsePipelineMetricsReturn = ReturnType<typeof usePipelineMetrics>;