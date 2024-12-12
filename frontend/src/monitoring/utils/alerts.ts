// src/monitoring/utils/alerts.ts
import type { Alert, AlertSeverity } from '../types/monitoring';

export const groupAlertsBySeverity = (alerts: Alert[]): Record<AlertSeverity, Alert[]> => {
  return alerts.reduce((acc, alert) => {
    if (!acc[alert.severity]) {
      acc[alert.severity] = [];
    }
    acc[alert.severity].push(alert);
    return acc;
  }, {} as Record<AlertSeverity, Alert[]>);
};

export const filterActiveAlerts = (alerts: Alert[]): Alert[] => {
  return alerts.filter(alert => !alert.resolved);
};

export const sortAlertsByPriority = (alerts: Alert[]): Alert[] => {
  const severityOrder: Record<AlertSeverity, number> = {
    critical: 0,
    warning: 1,
    info: 2
  };

  return [...alerts].sort((a, b) => {
    if (a.severity !== b.severity) {
      return severityOrder[a.severity] - severityOrder[b.severity];
    }
    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
  });
};

