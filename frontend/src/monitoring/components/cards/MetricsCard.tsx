// src/monitoring/components/charts/MetricsChart.tsx
import React from 'react';
import { Card } from '../../../common/components/ui/card';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';
import type { TimeSeriesData } from '../../types/monitoring';

interface MetricsChartProps {
  data: TimeSeriesData;
  title: string;
  className?: string;
}

export const MetricsCard: React.FC<MetricsChartProps> = ({
  data,
  title,
  className = ''
}) => {
  return (
    <Card className={className}>
      <div className="p-4">
        <h3 className="text-lg font-medium mb-4">{title}</h3>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.series[0].data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="timestamp" 
                tickFormatter={(value) => new Date(value).toLocaleTimeString()}
              />
              <YAxis />
              <Tooltip 
                labelFormatter={(value) => new Date(value).toLocaleString()}
                formatter={(value: number) => [value.toFixed(2), data.series[0].name]}
              />
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke="#8884d8" 
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Card>
  );
};

