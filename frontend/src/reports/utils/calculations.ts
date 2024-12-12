  // src/report/utils/calculations.ts
  type DataPoint = { value: number; timestamp: string };
  
  export function calculateTrend(data: DataPoint[]): {
    trend: number;
    direction: 'up' | 'down' | 'stable';
  } {
    if (data.length < 2) {
      return { trend: 0, direction: 'stable' };
    }
  
    const values = data.map(d => d.value);
    const firstValue = values[0];
    const lastValue = values[values.length - 1];
    const trend = ((lastValue - firstValue) / firstValue) * 100;
  
    return {
      trend,
      direction: trend > 1 ? 'up' : trend < -1 ? 'down' : 'stable'
    };
  }
  
  export function calculateStats(data: number[]): {
    min: number;
    max: number;
    avg: number;
    median: number;
  } {
    const sorted = [...data].sort((a, b) => a - b);
    const sum = sorted.reduce((acc, val) => acc + val, 0);
  
    return {
      min: sorted[0],
      max: sorted[sorted.length - 1],
      avg: sum / sorted.length,
      median: sorted[Math.floor(sorted.length / 2)]
    };
  }
 