import { dateUtils } from '@/common';
import { 
  ReportStatus, 
  ReportFormat, 
  ReportType,
  MetricStatus 
} from '../types/types';
import { REPORT_CONSTANTS } from '../constants';

/**
 * Status Formatting
 */
export function getStatusColor(status: ReportStatus): string {
  switch (status) {
    case 'completed':
      return 'text-green-600';
    case 'failed':
      return 'text-red-600';
    case 'generating':
      return 'text-blue-600';
    default:
      return 'text-gray-500';
  }
}

export function getStatusBadgeClass(status: ReportStatus): string {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    case 'generating':
      return 'bg-blue-100 text-blue-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

/**
 * Metric Formatting
 */
export function formatMetricValue(value: number, type: string): string {
  switch (type) {
    case 'percentage':
      return `${(value * 100).toFixed(1)}%`;
    case 'duration':
      return dateUtils.formatDetailedDuration(value);
    case 'count':
      return value.toLocaleString();
    default:
      return value.toFixed(2);
  }
}

export function getMetricStatusColor(status: MetricStatus): string {
  switch (status) {
    case 'healthy':
      return 'text-green-600';
    case 'warning':
      return 'text-yellow-600';
    case 'critical':
      return 'text-red-600';
    default:
      return 'text-gray-600';
  }
}

// Re-export commonly used date formatters
export const {
  formatDate,
  formatDetailedDuration,
  formatTimeAgoShort: formatTimeAgo,
} = dateUtils;