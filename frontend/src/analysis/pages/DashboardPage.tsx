// src/analysis/pages/DashboardPage.tsx
import React, { useEffect, useState } from "react";
import { useAnalysis } from "../hooks/useAnalysis";
import { useAnalysisDetails } from "../hooks/useAnalysisDetails";
import { Card, CardContent, CardHeader, CardTitle } from "@/common/components/ui/card";
import { Correlation, Anomaly, Pattern, Trend } from "../types/analysis";

export const DashboardPage: React.FC = () => {
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
      {/* Overview Section */}
      <section>
        <h1 className="text-2xl font-bold mb-4">Analytics Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Quality Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Total Issues</p>
                <p className="text-3xl font-bold">
                  {selectedQualityReport?.summary.totalIssues ?? 0}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Data Patterns</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Patterns Found</p>
                <p className="text-3xl font-bold">
                  {selectedInsightReport?.summary.patternsFound ?? 0}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Anomalies</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Detected</p>
                <p className="text-3xl font-bold">
                  {selectedInsightReport?.summary.anomaliesDetected ?? 0}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Detailed Analysis Sections */}
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
                    <span className="font-medium">
                      {correlation.confidence}%
                    </span>
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
                    <span className={`font-medium ${
                      anomaly.severity === 'high' ? 'text-red-600' :
                      anomaly.severity === 'medium' ? 'text-yellow-600' :
                      'text-blue-600'
                    }`}>
                      {anomaly.severity}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>Detection Time</span>
                    <span className="font-medium">
                      {new Date(anomaly.detectedAt).toLocaleString()}
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
                    <span className={`font-medium ${
                      trend.direction === 'increasing' ? 'text-green-600' :
                      trend.direction === 'decreasing' ? 'text-red-600' :
                      'text-yellow-600'
                    }`}>
                      {trend.direction}
                    </span>
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
    </div>
  );
};