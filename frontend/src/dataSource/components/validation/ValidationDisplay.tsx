// src/dataSource/components/validation/ValidationDisplay.tsx
import React from 'react';
import { Card } from '@/common/components/ui/card';
import { Alert, AlertTitle, AlertDescription } from '@/common/components/ui/alert';
import { ValidationIssue } from './ValidationIssue';
import type { ValidationDisplayProps } from './types';

export const ValidationDisplay: React.FC<ValidationDisplayProps> = ({
  validation,
  className = "",
  compact = false,
  showTitle = true
}) => {
  if (validation.isValid && !validation.warnings?.length) {
    return (
      <Alert className={className}>
        <AlertTitle>Validation Passed</AlertTitle>
        <AlertDescription>
          All validation checks passed successfully.
        </AlertDescription>
      </Alert>
    );
  }

  const ValidationContent = () => (
    <div className="space-y-4">
      {validation.issues.map((issue, index) => (
        <ValidationIssue
          key={`issue-${index}`}
          field={issue.field}
          type={issue.type}
          severity={issue.severity}
          message={issue.message}
        />
      ))}

      {validation.warnings?.map((warning, index) => (
        <ValidationIssue
          key={`warning-${index}`}
          field={warning.field}
          type="Warning"
          severity="warning"
          message={warning.message}
        />
      ))}
    </div>
  );

  if (compact) {
    return <div className={className}><ValidationContent /></div>;
  }

  return (
    <Card className={className}>
      <div className="p-4">
        {showTitle && <h3 className="text-lg font-medium mb-4">Validation Results</h3>}
        <ValidationContent />
      </div>
    </Card>
  );
};