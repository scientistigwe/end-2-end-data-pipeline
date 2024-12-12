// src/monitoring/components/alerts/AlertCard.tsx
import React from 'react';
import { Card, CardHeader, CardContent, CardFooter } from '../../../common/components/ui/card';
import { Button } from '../../../common/components/ui/button';
import { Badge } from '../../../common/components/ui/badge';
import { AlertTriangle, CheckCircle } from 'lucide-react';
import type { Alert } from '../../types/monitoring';

interface AlertCardProps {
  alert: Alert;
  onAcknowledge?: (alertId: string) => void;
  onResolve?: (alertId: string) => void;
  className?: string;
}

export const AlertCard: React.FC<AlertCardProps> = ({
  alert,
  onAcknowledge,
  onResolve,
  className = ''
}) => {
  const getSeverityColor = () => {
    switch (alert.severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'info':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-start justify-between">
        <div className="flex items-center space-x-2">
          {alert.severity === 'critical' ? (
            <AlertTriangle className="h-5 w-5 text-red-500" />
          ) : (
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
          )}
          <div>
            <Badge className={getSeverityColor()}>
              {alert.severity}
            </Badge>
            <h3 className="text-lg font-medium mt-1">{alert.metric}</h3>
          </div>
        </div>
        {alert.resolved && (
          <Badge variant="outline" className="text-green-600">
            <CheckCircle className="h-4 w-4 mr-1" />
            Resolved
          </Badge>
        )}
      </CardHeader>

      <CardContent className="space-y-2">
        <p>{alert.message}</p>
        <div className="text-sm text-muted-foreground">
          <p>Value: {alert.value} | Threshold: {alert.threshold}</p>
          <p>Time: {new Date(alert.timestamp).toLocaleString()}</p>
          {alert.resolved && alert.resolvedAt && (
            <p>Resolved at: {new Date(alert.resolvedAt).toLocaleString()}</p>
          )}
        </div>
      </CardContent>

      {!alert.resolved && (
        <CardFooter className="flex justify-end space-x-2">
          {!alert.acknowledged && onAcknowledge && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onAcknowledge(alert.id)}
            >
              Acknowledge
            </Button>
          )}
          {onResolve && (
            <Button
              size="sm"
              onClick={() => onResolve(alert.id)}
            >
              Resolve
            </Button>
          )}
        </CardFooter>
      )}
    </Card>
  );
};