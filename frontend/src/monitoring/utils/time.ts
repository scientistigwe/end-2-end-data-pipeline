// src/monitoring/utils/time.ts
export const calculateTimeRange = (
    interval: string
  ): { startTime: Date; endTime: Date } => {
    const endTime = new Date();
    const startTime = new Date();
  
    switch (interval) {
      case '1h':
        startTime.setHours(endTime.getHours() - 1);
        break;
      case '6h':
        startTime.setHours(endTime.getHours() - 6);
        break;
      case '24h':
        startTime.setHours(endTime.getHours() - 24);
        break;
      case '7d':
        startTime.setDate(endTime.getDate() - 7);
        break;
      case '30d':
        startTime.setDate(endTime.getDate() - 30);
        break;
      default:
        startTime.setHours(endTime.getHours() - 1);
    }
  
    return { startTime, endTime };
  };
  
  export const getTimeSeriesInterval = (timeRange: string): string => {
    switch (timeRange) {
      case '1h':
        return '1m';
      case '6h':
        return '5m';
      case '24h':
        return '15m';
      case '7d':
        return '1h';
      case '30d':
        return '6h';
      default:
        return '1m';
    }
  };
  
