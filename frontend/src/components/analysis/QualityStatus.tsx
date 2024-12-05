// src/components/analysis/QualityStatus.tsx
import React from "react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { QualityReport as QualityReportType } from "../../types/analysis";

interface QualityReportProps {
  report: QualityReportType;
  className?: string;
}

export const QualityReport: React.FC<QualityReportProps> = ({
  report,
  className = "",
}) => {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
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
        <h2 className="text-xl font-bold">Quality Analysis Report</h2>
        <div className="grid grid-cols-3 gap-4 mt-4">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold">
              {report.summary.totalIssues}
            </div>
            <div className="text-sm text-gray-600">Total Issues</div>
          </div>
          <div className="text-center p-4 bg-red-50 rounded-lg">
            <div className="text-2xl font-bold text-red-700">
              {report.summary.criticalIssues}
            </div>
            <div className="text-sm text-red-600">Critical Issues</div>
          </div>
          <div className="text-center p-4 bg-yellow-50 rounded-lg">
            <div className="text-2xl font-bold text-yellow-700">
              {report.summary.warningIssues}
            </div>
            <div className="text-sm text-yellow-600">Warning Issues</div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        <div>
          <h3 className="text-lg font-medium mb-4">Issues</h3>
          <div className="space-y-4">
            {report.issues.map((issue) => (
              <div key={issue.id} className="p-4 border rounded-lg space-y-2">
                <div className="flex justify-between items-start">
                  <div>
                    <Badge className={getSeverityColor(issue.severity)}>
                      {issue.severity}
                    </Badge>
                    <h4 className="text-md font-medium mt-2">{issue.type}</h4>
                  </div>
                </div>
                <p className="text-gray-600">{issue.description}</p>
                <div className="flex flex-wrap gap-2">
                  {issue.affectedColumns.map((column) => (
                    <Badge key={column} variant="outline">
                      {column}
                    </Badge>
                  ))}
                </div>
                {issue.possibleFixes && issue.possibleFixes.length > 0 && (
                  <div className="mt-2">
                    <h5 className="text-sm font-medium mb-1">
                      Possible Fixes:
                    </h5>
                    <ul className="list-disc pl-5 space-y-1">
                      {issue.possibleFixes.map((fix) => (
                        <li key={fix.id} className="text-sm">
                          {fix.description}
                          <Badge className="ml-2" variant="outline">
                            Impact: {fix.impact}
                          </Badge>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-lg font-medium mb-4">Recommendations</h3>
          <div className="space-y-4">
            {report.recommendations.map((rec) => (
              <div key={rec.id} className="p-4 border rounded-lg">
                <div className="flex justify-between items-start">
                  <div>
                    <Badge className="bg-blue-100 text-blue-800">
                      {rec.type}
                    </Badge>
                    <p className="mt-2">{rec.description}</p>
                  </div>
                  <Badge variant="outline">Impact: {rec.impact}</Badge>
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
