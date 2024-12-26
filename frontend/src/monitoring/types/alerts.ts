// src/monitoring/types/alerts.ts
import type { AlertSeverity } from './base';

export interface AlertConfig {
  metric: string;
  threshold: number;
  severity: AlertSeverity;
  condition: 'above' | 'below' | 'equals';
  enabled?: boolean;
  description?: string;
  name: string;
}

export interface Alert {
  id: string;
  configId: string;
  timestamp: string;
  metric: string;
  value: number;
  threshold: number;
  condition: 'above' | 'below' | 'equals';
  severity: AlertSeverity;
  status: 'active' | 'acknowledged' | 'resolved';
  acknowledgedBy?: string;
  resolvedBy?: string;
  resolution?: AlertResolution;
}

export interface AlertResolution {
  timestamp: string;
  comment?: string;
  action?: string;
}