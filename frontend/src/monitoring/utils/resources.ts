// src/monitoring/utils/resources.ts
export const calculateResourceUtilization = (usage: ResourceUsage): {
    cpu: number;
    memory: number;
    disk: number;
  } => {
    return {
      cpu: (usage.cpu.used / usage.cpu.total) * 100,
      memory: (usage.memory.used / usage.memory.total) * 100,
      disk: (usage.disk.used / usage.disk.total) * 100
    };
  };
  
  export const getResourceHealthStatus = (utilization: number): MetricStatus => {
    if (utilization >= MONITORING_CONFIG.CRITICAL_THRESHOLD) return 'critical';
    if (utilization >= MONITORING_CONFIG.WARNING_THRESHOLD) return 'warning';
    return 'healthy';
  };