// src/components/datasource/DataSourceValidation.tsx
import React from "react";
import { Card, CardHeader, CardContent } from "../../../../components/ui/card";
import { Badge } from "../../../../components/ui/badge";
import type { ValidationResult } from "../types/dataSources";

interface DataSourceValidationProps {
  validation: ValidationResult;
  className?: string;
}

export const DataSourceValidation: React.FC<DataSourceValidationProps> = ({
  validation,
  className = "",
}) => {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "error":
        return "bg-red-100 text-red-800";
      case "warning":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-blue-100 text-blue-800";
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex justify-between items-center">
          <h3 className="font-medium">Validation Results</h3>
          <Badge
            className={
              validation.isValid
                ? "bg-green-100 text-green-800"
                : "bg-red-100 text-red-800"
            }
          >
            {validation.isValid ? "Valid" : "Invalid"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {validation.issues.length > 0 && (
          <div className="space-y-4">
            <h4 className="text-sm font-medium">Issues Found</h4>
            <div className="space-y-2">
              {validation.issues.map((issue, index) => (
                <div key={index} className="p-3 rounded-md border">
                  <div className="flex items-start space-x-2">
                    <Badge className={getSeverityColor(issue.severity)}>
                      {issue.severity}
                    </Badge>
                    <div>
                      <p>{issue.message}</p>
                      {issue.field && (
                        <p className="text-sm text-gray-500">
                          Field: {issue.field}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {validation.warnings.length > 0 && (
          <div className="space-y-4 mt-4">
            <h4 className="text-sm font-medium">Warnings</h4>
            <div className="space-y-2">
              {validation.warnings.map((warning, index) => (
                <div key={index} className="p-3 rounded-md bg-yellow-50">
                  <p>{warning.message}</p>
                  {warning.field && (
                    <p className="text-sm text-gray-500">
                      Field: {warning.field}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
