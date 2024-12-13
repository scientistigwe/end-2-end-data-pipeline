import { dateUtils } from '@/common';
import { PIPELINE_CONSTANTS } from '../constants';
import type { PipelineStatus, LogLevel } from '../types/pipeline';

/**
 * Status and Level Formatting
 */
export function getStatusColor(status: PipelineStatus): string {
  switch (status) {
    case 'running':
      return 'bg-blue-100 text-blue-800';
    case 'completed':
      return 'bg-green-100 text-green-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    case 'paused':
      return 'bg-yellow-100 text-yellow-800';
    case 'cancelled':
      return 'bg-gray-500 text-white';
    case 'idle':
      return 'bg-gray-100 text-gray-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

export function getLogLevelColor(level: LogLevel): string {
  switch (level) {
    case 'error':
      return 'bg-red-100 text-red-800';
    case 'warn':
      return 'bg-yellow-100 text-yellow-800';
    case 'info':
    default:
      return 'bg-blue-100 text-blue-800';
  }
}

/**
 * Metric Formatting
 */
export function formatMetricValue(metric: string, value: number): string {
  switch (metric) {
    case 'throughput':
      return `${value.toFixed(2)}/s`;
    case 'latency':
      return `${value.toFixed(2)}ms`;
    case 'errorRate':
      return `${(value * 100).toFixed(2)}%`;
    case 'cpu':
    case 'memory':
      return `${(value * 100).toFixed(1)}%`;
    default:
      return value.toFixed(2);
  }
}

export function getMetricColor(metric: string): string {
  switch (metric) {
    case 'errorRate':
      return '#ef4444';
    case 'latency':
      return '#f59e0b';
    case 'throughput':
      return '#10b981';
    default:
      return '#6366f1';
  }
}

// Re-export date formatting functions
export const formatDetailedDuration = dateUtils.formatDetailedDuration;
export const formatTimeAgoShort = dateUtils.formatTimeAgoShort;
export const formatDate = dateUtils.formatDate;

// Re-export the type if needed elsewhere
export type { DateFormatOptions } from '@/common/utils/date/dateUtils';