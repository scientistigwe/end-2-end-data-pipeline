// src/analysis/components/reports/QualityReport.tsx
import React from "react";
import { Card, CardHeader, CardContent } from "@/common/components/ui/card";
import { Badge } from "@/common/components/ui/badge";
import { cn } from "@/common/utils/cn";
import type { QualityReport as QualityReportType } from "../../types/analysis";

// Move this to a component-specific utility or keep it inline since it's specific to QualityReport
const getQualityIssueSeverityColor = (severity: string): string => {
  switch (severity) {
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

interface QualityReportProps {
  report: QualityReportType;
  className?: string;
}

export const QualityReport: React.FC<QualityReportProps> = ({
  report,
  className = "",
}) => {
  return (
    <Card className={cn("", className)}>
      <CardHeader>
        <h2 className="text-xl font-bold">Quality Analysis Report</h2>
        <MetricsSummary summary={report.summary} />
      </CardHeader>

      <CardContent className="space-y-6">
        <IssuesList issues={report.issues} />
        <RecommendationsList recommendations={report.recommendations} />
      </CardContent>
    </Card>
  );
};

// Extracted Components
const MetricsSummary: React.FC<{ summary: QualityReportType['summary'] }> = ({ summary }) => (
  <div className="grid grid-cols-3 gap-4 mt-4">
    <MetricCard
      value={summary.totalIssues}
      label="Total Issues"
      className="bg-gray-50"
    />
    <MetricCard
      value={summary.criticalIssues}
      label="Critical Issues"
      className="bg-red-50 text-red-700"
      labelClassName="text-red-600"
    />
    <MetricCard
      value={summary.warningIssues}
      label="Warning Issues"
      className="bg-yellow-50 text-yellow-700"
      labelClassName="text-yellow-600"
    />
  </div>
);

const MetricCard: React.FC<{
  value: number;
  label: string;
  className?: string;
  labelClassName?: string;
}> = ({ value, label, className, labelClassName }) => (
  <div className={cn("text-center p-4 rounded-lg", className)}>
    <div className="text-2xl font-bold">{value}</div>
    <div className={cn("text-sm", labelClassName)}>{label}</div>
  </div>
);

const IssuesList: React.FC<{ issues: QualityReportType['issues'] }> = ({ issues }) => (
  <div>
    <h3 className="text-lg font-medium mb-4">Issues</h3>
    <div className="space-y-4">
      {issues.map((issue) => (
        <IssueCard key={issue.id} issue={issue} />
      ))}
    </div>
  </div>
);

const IssueCard: React.FC<{ issue: QualityReportType['issues'][0] }> = ({ issue }) => (
  <div className="p-4 border rounded-lg space-y-2">
    <div className="flex justify-between items-start">
      <div>
        <Badge className={getQualityIssueSeverityColor(issue.severity)}>
          {issue.severity}
        </Badge>
        <h4 className="text-md font-medium mt-2">{issue.type}</h4>
      </div>
    </div>
    <p className="text-gray-600">{issue.description}</p>
    <AffectedColumns columns={issue.affectedColumns} />
    <PossibleFixes fixes={issue.possibleFixes} />
  </div>
);

const AffectedColumns: React.FC<{ columns: string[] }> = ({ columns }) => (
  <div className="flex flex-wrap gap-2">
    {columns.map((column) => (
      <Badge key={column} variant="outline">
        {column}
      </Badge>
    ))}
  </div>
);

const PossibleFixes: React.FC<{
  fixes?: QualityReportType['issues'][0]['possibleFixes']
}> = ({ fixes }) => {
  if (!fixes?.length) return null;

  return (
    <div className="mt-2">
      <h5 className="text-sm font-medium mb-1">Possible Fixes:</h5>
      <ul className="list-disc pl-5 space-y-1">
        {fixes.map((fix) => (
          <li key={fix.id} className="text-sm">
            {fix.description}
            <Badge className="ml-2" variant="outline">
              Impact: {fix.impact}
            </Badge>
          </li>
        ))}
      </ul>
    </div>
  );
};

const RecommendationsList: React.FC<{
  recommendations: QualityReportType['recommendations']
}> = ({ recommendations }) => (
  <div>
    <h3 className="text-lg font-medium mb-4">Recommendations</h3>
    <div className="space-y-4">
      {recommendations.map((rec) => (
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
);