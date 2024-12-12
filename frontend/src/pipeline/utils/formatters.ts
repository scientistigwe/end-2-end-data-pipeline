// src/pipeline/utils/formatters.ts
import { PIPELINE_CONSTANTS } from '../constants';
import type { PipelineStatus, LogLevel } from '../types/pipeline';

/**
 * Time and Duration Formatting
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  }
  return `${seconds}s`;
}

export function formatTimeAgo(date: string | Date): string {
  const now = new Date();
  const past = new Date(date);
  const diffMs = now.getTime() - past.getTime();
  
  const diffMinutes = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHours > 0) return `${diffHours}h ago`;
  if (diffMinutes > 0) return `${diffMinutes}m ago`;
  return 'just now';
}

export function formatDateTime(date: string | Date): string {
  return new Date(date).toLocaleString();
}

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
    case 'error':
      return 'bg-red-100 text-red-800';
    case 'paused':
      return 'bg-yellow-100 text-yellow-800';
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

