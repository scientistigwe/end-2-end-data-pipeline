
// src/monitoring/components/resources/ResourceUsageCard.tsx
import React from 'react';
import { Card, CardHeader, CardContent } from '../../../common/components/ui/card';
import { Progress } from '../../../common/components/ui/progress';
import type { ResourceUsage } from '../../types/monitoring';

interface ResourceUsageCardProps {
  resources: ResourceUsage;
  className?: string;
}

export const ResourceUsageCard: React.FC<ResourceUsageCardProps> = ({
  resources,
  className = ''
}) => {
  const formatBytes = (bytes: number): string => {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let value = bytes;
    let unitIndex = 0;
    
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex++;
    }
    
    return `${value.toFixed(1)} ${units[unitIndex]}`;
  };

  const getUsageColor = (percentage: number): string => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <Card className={className}>
      <CardHeader>
        <h3 className="font-medium">Resource Usage</h3>
      </CardHeader>

      <CardContent>
        <div className="space-y-6">
          {/* CPU Usage */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>CPU Usage</span>
              <span>{resources.cpu.percentage.toFixed(1)}%</span>
            </div>
            <Progress 
              value={resources.cpu.percentage} 
              className={getUsageColor(resources.cpu.percentage)}
            />
          </div>

          {/* Memory Usage */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Memory Usage</span>
              <span>
                {formatBytes(resources.memory.used)} / {formatBytes(resources.memory.total)}
              </span>
            </div>
            <Progress 
              value={resources.memory.percentage}
              className={getUsageColor(resources.memory.percentage)}
            />
          </div>

          {/* Disk Usage */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Disk Usage</span>
              <span>
                {formatBytes(resources.disk.used)} / {formatBytes(resources.disk.total)}
              </span>
            </div>
            <Progress 
              value={resources.disk.percentage}
              className={getUsageColor(resources.disk.percentage)}
            />
          </div>

          <div className="text-sm text-muted-foreground pt-2 border-t">
            Last updated: {new Date(resources.timestamp).toLocaleString()}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
