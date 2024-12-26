// src/dataSource/components/validation/ValidationResult.tsx
import React from "react";
import {
  Alert,
  AlertTitle,
  AlertDescription,
} from "../../../common/components/ui/alert";
import { Badge } from "../../../common/components/ui/badge";
import { AlertCircle, AlertTriangle, Info } from "lucide-react";
import type { ValidationResult as ValidationResultType } from "../../types/base";

interface ValidationResultProps {
  validation: ValidationResultType;
  className?: string;
}

export const ValidationResult: React.FC<ValidationResultProps> = ({
  validation,
  className = "",
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

  return (
    <div className={`space-y-4 ${className}`}>
      {validation.issues.map((issue, index) => (
        <Alert key={index} variant={getVariant(issue.severity)}>
          <div className="flex gap-2">
            {getIcon(issue.severity)}
            <div>
              <div className="flex items-center gap-2">
                {issue.field && <Badge variant="outline">{issue.field}</Badge>}
                <span>{issue.type}</span>
              </div>
              <p className="mt-1 text-sm">{issue.message}</p>
            </div>
          </div>
        </Alert>
      ))}

      {validation.warnings?.map((warning, index) => (
        <Alert key={index} variant="warning">
          <div className="flex gap-2">
            <AlertTriangle className="h-4 w-4" />
            <p>{warning.message}</p>
          </div>
        </Alert>
      ))}
    </div>
  );
};
