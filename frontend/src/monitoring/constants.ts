// src/monitoring/constants.ts
export const MONITORING_CONFIG = {
    REFRESH_INTERVAL: 5000,
    HEALTH_CHECK_INTERVAL: 10000,
    RESOURCE_CHECK_INTERVAL: 10000,
    ALERT_HISTORY_LIMIT: 100,
    METRIC_RETENTION_DAYS: 30,
    CRITICAL_THRESHOLD: 90,
    WARNING_THRESHOLD: 70
  } as const;
  
  export const MONITORING_MESSAGES = {
    ERRORS: {
      START_FAILED: 'Failed to start monitoring',
      METRICS_FETCH_FAILED: 'Failed to fetch metrics',
      HEALTH_FETCH_FAILED: 'Failed to fetch health status',
      RESOURCE_FETCH_FAILED: 'Failed to fetch resource usage',
      ALERT_CONFIG_FAILED: 'Failed to configure alerts',
      ALERT_HISTORY_FAILED: 'Failed to fetch alert history',
      ALERT_ACKNOWLEDGE_FAILED: 'Failed to acknowledge alert',
      ALERT_RESOLVE_FAILED: 'Failed to resolve alert'
    },
    SUCCESS: {
      MONITORING_STARTED: 'Monitoring started successfully',
      ALERT_CONFIGURED: 'Alert configuration updated',
      ALERT_ACKNOWLEDGED: 'Alert acknowledged successfully',
      ALERT_RESOLVED: 'Alert resolved successfully'
    }
  } as const;
  
  export const MONITORING_STATUS = {
    HEALTHY: 'healthy',
    WARNING: 'warning',
    CRITICAL: 'critical'
  } as const;
  
  export const ALERT_SEVERITY = {
    INFO: 'info',
    WARNING: 'warning',
    CRITICAL: 'critical'
  } as const;