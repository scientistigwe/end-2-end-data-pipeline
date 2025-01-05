// src/dataSource/components/validation/ValidationIssue.tsx
import React from 'react';
import { Alert } from '@/common/components/ui/alert';
import { Badge } from '@/common/components/ui/badge';
import { AlertCircle, AlertTriangle, Info } from 'lucide-react';
import type { ValidationIssueProps } from './types';

export const ValidationIssue: React.FC<ValidationIssueProps> = ({
  field,
  type,
  severity,
  message,
}) => {
  const getIcon = (severity: string) => {
    switch (severity) {
      case "error":
        return <AlertCircle className="h-4 w-4" />;
      case "warning":
        return <AlertTriangle className="h-4 w-4" />;
      default:
        return <Info className="h-4 w-4" />;
    }
  };

  const getVariant = (severity: string) => {
    switch (severity) {
      case "error":
        return "destructive";
      case "warning":
        return "warning";
      default:
        return "default";
    }
  };

  return (
    <Alert variant={getVariant(severity)}>
      <div className="flex gap-2">
        {getIcon(severity)}
        <div>
          <div className="flex items-center gap-2">
            {field && <Badge variant="outline">{field}</Badge>}
            <span>{type}</span>
          </div>
          <p className="mt-1 text-sm">{message}</p>
        </div>
      </div>
    </Alert>
  );
};