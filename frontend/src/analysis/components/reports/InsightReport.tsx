// src/analysis/components/reports/InsightReport.tsx
import React from "react";
import { Card, CardHeader, CardContent } from "@/common/components/ui/card";
import { Badge } from "@/common/components/ui/badge";
import { cn } from "@/common/utils/cn";
import { dateUtils } from "@/common";
import type { InsightReport as InsightReportType } from "../../types/analysis";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface InsightReportProps {
  report: InsightReportType;
  className?: string;
}

export const InsightReport: React.FC<InsightReportProps> = ({
  report,
  className = "",
}) => {
  return (
    <Card className={cn("", className)}>
      <CardHeader>
        <h2 className="text-xl font-bold">Insight Analysis Report</h2>
        <InsightSummary summary={report.summary} />
      </CardHeader>

      <CardContent className="space-y-6">
        <PatternSection patterns={report.patterns} />
        <AnomalySection anomalies={report.anomalies} />
        <CorrelationSection correlations={report.correlations} />
      </CardContent>
    </Card>
  );
};

const InsightSummary: React.FC<{ summary: InsightReportType["summary"] }> = ({
  summary,
}) => (
  <div className="grid grid-cols-4 gap-4 mt-4">
    <MetricCard
      value={summary.patternsFound}
      label="Patterns Found"
      className="bg-blue-50 text-blue-700"
    />
    <MetricCard
      value={summary.anomaliesDetected}
      label="Anomalies"
      className="bg-red-50 text-red-700"
    />
    <MetricCard
      value={summary.correlationsIdentified}
      label="Correlations"
      className="bg-green-50 text-green-700"
    />
    <MetricCard
      value={summary.confidenceLevel}
      label="Confidence"
      className="bg-purple-50 text-purple-700"
      suffix="%"
    />
  </div>
);

const MetricCard: React.FC<{
  value: number;
  label: string;
  className?: string;
  suffix?: string;
}> = ({ value, label, className, suffix = "" }) => (
  <div className={cn("text-center p-4 rounded-lg", className)}>
    <div className="text-2xl font-bold">
      {value}
      {suffix}
    </div>
    <div className="text-sm opacity-80">{label}</div>
  </div>
);

const PatternSection: React.FC<{ patterns: InsightReportType["patterns"] }> = ({
  patterns,
}) => (
  <div>
    <h3 className="text-lg font-medium mb-4">Identified Patterns</h3>
    <div className="grid gap-4 md:grid-cols-2">
      {patterns.map((pattern) => (
        <Card key={pattern.id} className="p-4">
          <h4 className="font-medium mb-2">{pattern.name}</h4>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Occurrence Rate</span>
              <span>{pattern.occurrenceRate}%</span>
            </div>
            <div className="flex justify-between text-sm">
              <span>Confidence</span>
              <span>{pattern.confidence}%</span>
            </div>
            <p className="text-sm text-gray-600 mt-2">{pattern.description}</p>
            <div className="flex flex-wrap gap-2 mt-2">
              {pattern.affectedFields.map((field) => (
                <Badge key={field} variant="outline">
                  {field}
                </Badge>
              ))}
            </div>
          </div>
        </Card>
      ))}
    </div>
  </div>
);

const AnomalySection: React.FC<{
  anomalies: InsightReportType["anomalies"];
}> = ({ anomalies }) => (
  <div>
    <h3 className="text-lg font-medium mb-4">Detected Anomalies</h3>
    <div className="grid gap-4 md:grid-cols-2">
      {anomalies.map((anomaly) => (
        <Card key={anomaly.id} className="p-4">
          <div className="flex justify-between items-start mb-2">
            <h4 className="font-medium">{anomaly.type}</h4>
            <Badge className={getSeverityClass(anomaly.severity)}>
              {anomaly.severity}
            </Badge>
          </div>
          <p className="text-sm text-gray-600 mb-2">{anomaly.description}</p>
          <div className="text-sm text-gray-500">
            Detected:{" "}
            {dateUtils.formatDate(anomaly.detectedAt, { includeTime: true })}
          </div>
        </Card>
      ))}
    </div>
  </div>
);

const CorrelationSection: React.FC<{
  correlations: InsightReportType["correlations"];
}> = ({ correlations }) => (
  <div>
    <h3 className="text-lg font-medium mb-4">Correlations</h3>
    <div className="grid gap-4">
      {correlations.map((correlation) => (
        <Card key={correlation.id} className="p-4">
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h4 className="font-medium">
                {correlation.sourceField} → {correlation.targetField}
              </h4>
              <Badge variant="outline">
                {(correlation.strength * 100).toFixed(1)}% Strength
              </Badge>
            </div>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={generateCorrelationData(correlation)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#8884d8"
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="text-sm text-gray-600">{correlation.description}</p>
            <div className="flex flex-wrap gap-2">
              {correlation.columns.map((column) => (
                <Badge key={column} variant="outline">
                  {column}
                </Badge>
              ))}
            </div>
          </div>
        </Card>
      ))}
    </div>
  </div>
);

// Utility functions
const getSeverityClass = (severity: string): string => {
  switch (severity) {
    case "high":
      return "bg-red-100 text-red-800";
    case "medium":
      return "bg-yellow-100 text-yellow-800";
    case "low":
      return "bg-blue-100 text-blue-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
};

const generateCorrelationData = (
  correlation: InsightReportType["correlations"][0]
) => {
  // Generate sample data points for visualization
  return Array.from({ length: 10 }, (_, i) => ({
    name: `Point ${i + 1}`,
    value: correlation.strength * Math.random() * 100,
  }));
};
