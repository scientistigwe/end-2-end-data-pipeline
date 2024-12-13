// src/analysis/pages/DashboardPage.tsx
import React, { useEffect, useState } from "react";
import { useAnalysis } from "../hooks/useAnalysis";
import { useAnalysisDetails } from "../hooks/useAnalysisDetails";
import { Card, CardContent, CardHeader, CardTitle } from "@/common/components/ui/card";
import { Badge } from "@/common/components/ui/badge";
import { dateUtils } from "@/common";
import type { Correlation, Anomaly, Pattern, Trend } from "../types/analysis";

const DashboardPage: React.FC = () => {
  const {
    selectedAnalysis,
    selectedQualityReport,
    selectedInsightReport
  } = useAnalysis();

  const {
    getCorrelations,
    getAnomalies,
    getTrends,
    getPatternDetails
  } = useAnalysisDetails();

  const [correlations, setCorrelations] = useState<Correlation[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const fetchDetails = async () => {
      if (selectedAnalysis?.id) {
        setIsLoading(true);
        try {
          const [
            correlationsData,
            anomaliesData,
            trendsData
          ] = await Promise.all([
            getCorrelations(selectedAnalysis.id),
            getAnomalies(selectedAnalysis.id),
            getTrends(selectedAnalysis.id)
          ]);

          setCorrelations(correlationsData);
          setAnomalies(anomaliesData);
          setTrends(trendsData);

          if (selectedInsightReport?.patterns) {
            const patternDetails = await Promise.all(
              selectedInsightReport.patterns.map(pattern =>
                getPatternDetails(selectedAnalysis.id, pattern.id)
              )
            );
            setPatterns(patternDetails);
          }
        } catch (error) {
          console.error('Failed to fetch analysis details:', error);
        } finally {
          setIsLoading(false);
        }
      }
    };

    fetchDetails();
  }, [
    selectedAnalysis?.id,
    selectedInsightReport?.patterns,
    getCorrelations,
    getAnomalies,
    getTrends,
    getPatternDetails
  ]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-lg">Loading analysis details...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <section>
        <h1 className="text-2xl font-bold mb-4">Analytics Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            title="Quality Metrics"
            value={selectedQualityReport?.summary.totalIssues ?? 0}
            label="Total Issues"
          />
          <MetricCard
            title="Data Patterns"
            value={selectedInsightReport?.summary.patternsFound ?? 0}
            label="Patterns Found"
          />
          <MetricCard
            title="Anomalies"
            value={selectedInsightReport?.summary.anomaliesDetected ?? 0}
            label="Detected"
          />
        </div>
      </section>

      <CorrelationSection correlations={correlations} />
      <AnomalySection anomalies={anomalies} />
      <PatternSection patterns={patterns} />
      <TrendSection trends={trends} />
    </div>
  );
};

// Extracted Components
const MetricCard: React.FC<{
  title: string;
  value: number;
  label: string;
}> = ({ title, value, label }) => (
  <Card>
    <CardHeader>
      <CardTitle>{title}</CardTitle>
    </CardHeader>
    <CardContent>
      <div className="space-y-2">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-3xl font-bold">{value}</p>
      </div>
    </CardContent>
  </Card>
);

const CorrelationSection: React.FC<{ correlations: Correlation[] }> = ({ correlations }) => (
  <section>
    <h2 className="text-xl font-semibold mb-4">Correlation Analysis</h2>
    <div className="grid grid-cols-1 gap-4">
      {correlations.map((correlation) => (
        <Card key={correlation.id}>
          <CardHeader>
            <CardTitle>
              {correlation.sourceField} → {correlation.targetField}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span>Correlation Strength</span>
                <span className="font-medium">
                  {(correlation.strength * 100).toFixed(2)}%
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span>Confidence Level</span>
                <span className="font-medium">{correlation.confidence}%</span>
              </div>
              <p className="text-sm text-muted-foreground">
                {correlation.description}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  </section>
);

const AnomalySection: React.FC<{ anomalies: Anomaly[] }> = ({ anomalies }) => (
  <section>
    <h2 className="text-xl font-semibold mb-4">Anomaly Trends</h2>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {anomalies.map((anomaly) => (
        <Card key={anomaly.id}>
          <CardHeader>
            <CardTitle>{anomaly.type}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span>Severity</span>
                <Badge variant={
                  anomaly.severity === 'high' ? 'destructive' :
                  anomaly.severity === 'medium' ? 'warning' :
                  'default'
                }>
                  {anomaly.severity}
                </Badge>
              </div>
              <div className="flex justify-between items-center">
                <span>Detection Time</span>
                <span className="font-medium">
                  {dateUtils.formatDate(anomaly.detectedAt, { includeTime: true })}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                {anomaly.description}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  </section>
);

const PatternSection: React.FC<{ patterns: Pattern[] }> = ({ patterns }) => (
  <section>
    <h2 className="text-xl font-semibold mb-4">Pattern Breakdown</h2>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {patterns.map((pattern) => (
        <Card key={pattern.id}>
          <CardHeader>
            <CardTitle>{pattern.name}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span>Occurrence Rate</span>
                <span className="font-medium">
                  {pattern.occurrenceRate}%
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span>Confidence Level</span>
                <span className="font-medium">
                  {pattern.confidence}%
                </span>
              </div>
              <div className="text-sm text-muted-foreground">
                <h4 className="font-medium mb-2">Affected Fields:</h4>
                <ul className="list-disc pl-4">
                  {pattern.affectedFields.map((field, i) => (
                    <li key={i}>{field}</li>
                  ))}
                </ul>
              </div>
              <p className="text-sm text-muted-foreground">
                {pattern.description}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  </section>
);

const TrendSection: React.FC<{ trends: Trend[] }> = ({ trends }) => (
  <section>
    <h2 className="text-xl font-semibold mb-4">Trend Analysis</h2>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {trends.map((trend) => (
        <Card key={trend.id}>
          <CardHeader>
            <CardTitle>{trend.name}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span>Direction</span>
                <Badge variant={
                  trend.direction === 'increasing' ? 'success' :
                  trend.direction === 'decreasing' ? 'destructive' :
                  'warning'
                }>
                  {trend.direction}
                </Badge>
              </div>
              <div className="flex justify-between items-center">
                <span>Strength</span>
                <span className="font-medium">
                  {trend.strength}%
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span>Time Period</span>
                <span className="font-medium">
                  {trend.timePeriod}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                {trend.description}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  </section>
);

export default DashboardPage;