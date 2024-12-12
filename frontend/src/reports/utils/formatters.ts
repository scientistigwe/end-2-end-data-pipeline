// src/report/utils/formatters.ts
import { 
    ReportStatus, 
    ReportFormat, 
    ReportType,
    MetricStatus 
  } from '../types/report';
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
   * Date and Time Formatting
   */
  export function formatDateTime(date: string | Date): string {
    return new Date(date).toLocaleString();
  }
  
  export function formatDuration(ms: number): string {
    if (ms < 1000) return `${ms}ms`;
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
  
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
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
  
  /**
   * Metric Formatting
   */
  export function formatMetricValue(value: number, type: string): string {
    switch (type) {
      case 'percentage':
        return `${(value * 100).toFixed(1)}%`;
      case 'duration':
        return formatDuration(value);
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
  