// src/monitoring/services/monitoringService.ts
import { MonitoringApi } from '../api/monitoringApi';
import { handleApiError } from '../../common/utils/api/apiUtils';
import { formatDate } from '@/common/utils/date/dateUtils';
import { MONITORING_MESSAGES } from '../constants';
import type {
  MonitoringConfig,
  MetricsData,
  SystemHealth,
  AlertConfig,
  Alert,
  ResourceUsage,
} from '../types/monitoring';

export class MonitoringService {
  static async startMonitoring(
    pipelineId: string,
    config: MonitoringConfig
  ): Promise<void> {
    try {
      await MonitoringApi.startMonitoring(pipelineId, config);
    } catch (err) {
      handleApiError(err);
      throw new Error(MONITORING_MESSAGES.ERRORS.START_FAILED);
    }
  }

  static async getMetrics(pipelineId: string): Promise<MetricsData> {
    try {
      const response = await MonitoringApi.getMetrics(pipelineId);
      return this.transformMetrics(response.data);
    } catch (err) {
      handleApiError(err);
      throw new Error(MONITORING_MESSAGES.ERRORS.METRICS_FETCH_FAILED);
    }
  }

  static async getHealth(pipelineId: string): Promise<SystemHealth> {
    try {
      const response = await MonitoringApi.getHealth(pipelineId);
      return this.transformHealth(response.data);
    } catch (err) {
      handleApiError(err);
      throw new Error(MONITORING_MESSAGES.ERRORS.HEALTH_FETCH_FAILED);
    }
  }

  static async getResourceUsage(pipelineId: string): Promise<ResourceUsage> {
    try {
      const response = await MonitoringApi.getResourceUsage(pipelineId);
      return this.transformResourceUsage(response.data);
    } catch (err) {
      handleApiError(err);
      throw new Error(MONITORING_MESSAGES.ERRORS.RESOURCE_FETCH_FAILED);
    }
  }

  static async configureAlerts(
    pipelineId: string,
    config: AlertConfig
  ): Promise<void> {
    try {
      await MonitoringApi.configureAlerts(pipelineId, config);
    } catch (err) {
      handleApiError(err);
      throw new Error(MONITORING_MESSAGES.ERRORS.ALERT_CONFIG_FAILED);
    }
  }

  static async getAlertHistory(pipelineId: string): Promise<Alert[]> {
    try {
      const response = await MonitoringApi.getAlertHistory(pipelineId);
      return response.data.map(this.transformAlert);
    } catch (err) {
      handleApiError(err);
      throw new Error(MONITORING_MESSAGES.ERRORS.ALERT_HISTORY_FAILED);
    }
  }

  static async acknowledgeAlert(pipelineId: string, alertId: string): Promise<void> {
    try {
      await MonitoringApi.acknowledgeAlert(pipelineId, alertId);
    } catch (err) {
      handleApiError(err);
      throw new Error(MONITORING_MESSAGES.ERRORS.ALERT_ACKNOWLEDGE_FAILED);
    }
  }

  static async resolveAlert(
    pipelineId: string,
    alertId: string,
    resolution?: { comment?: string; action?: string }
  ): Promise<void> {
    try {
      await MonitoringApi.resolveAlert(pipelineId, alertId, resolution);
    } catch (err) {
      handleApiError(err);
      throw new Error(MONITORING_MESSAGES.ERRORS.ALERT_RESOLVE_FAILED);
    }
  }

  // Data Transformations
  private static transformMetrics(metrics: MetricsData): MetricsData {
    return {
      ...metrics,
      timestamp: formatDate(metrics.timestamp)
    };
  }

  private static transformHealth(health: SystemHealth): SystemHealth {
    return {
      ...health,
      lastChecked: formatDate(health.lastChecked),
      components: health.components.map(component => ({
        ...component,
        lastChecked: component.lastChecked ? formatDate(component.lastChecked) : undefined
      }))
    };
  }

  private static transformResourceUsage(usage: ResourceUsage): ResourceUsage {
    return {
      ...usage,
      timestamp: formatDate(usage.timestamp)
    };
  }

  private static transformAlert(alert: Alert): Alert {
    return {
      ...alert,
      timestamp: formatDate(alert.timestamp),
      resolvedAt: alert.resolvedAt ? formatDate(alert.resolvedAt) : undefined
    };
  }

  // Utility Methods
  static calculateResourcePercentage(used: number, total: number): number {
    return (used / total) * 100;
  }

  static isResourceCritical(percentage: number): boolean {
    return percentage >= 90;
  }

  static isResourceWarning(percentage: number): boolean {
    return percentage >= 70 && percentage < 90;
  }

  static getStatusSeverity(status: string): 'critical' | 'warning' | 'healthy' {
    switch (status.toLowerCase()) {
      case 'critical':
        return 'critical';
      case 'warning':
        return 'warning';
      default:
        return 'healthy';
    }
  }
}

export default MonitoringService;

