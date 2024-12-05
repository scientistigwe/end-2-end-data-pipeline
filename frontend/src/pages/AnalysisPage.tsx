// src/pages/AnalysisPage.tsx
import React, { useState } from "react";
import { useQualityAnalysis } from "../hooks/analytics/useQualityAnalysis";
import { useInsightAnalysis } from "../hooks/analytics/useAnalysis";
import {
  QualityAnalysisHookResult,
  InsightAnalysisHookResult,
} from "../hooks/analytics/types";

export const AnalysisPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"quality" | "insight">("quality");

  const {
    startAnalysis: startQuality,
    report: qualityReport,
    isStarting: isQualityStarting,
  } = useQualityAnalysis("pipeline-123") as QualityAnalysisHookResult;

  const {
    startAnalysis: startInsight,
    report: insightReport,
    isStarting: isInsightStarting,
  } = useInsightAnalysis("pipeline-123") as InsightAnalysisHookResult;

  const handleStartQuality = () => {
    startQuality({
      rules: {
        dataTypes: true, // Updated to match the type definition
        nullChecks: true,
        rangeValidation: true,
        customRules: {
          accuracy: true,
          completeness: true,
        },
      },
      thresholds: {
        errorThreshold: 0.1,
        warningThreshold: 0.2,
      },
    });
  };

  const handleStartInsight = () => {
    startInsight({
      analysisTypes: {
        patterns: true,
        correlations: true,
        anomalies: true,
      },
      dataScope: {
        columns: ["column1", "column2"],
        timeRange: {
          start: "2024-01-01",
          end: "2024-12-31",
        },
      },
    });
  };

  return (
    <div className="space-y-6">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Analysis</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* Analysis Type Tabs */}
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab("quality")}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm
                ${
                  activeTab === "quality"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }
              `}
            >
              Quality Analysis
            </button>
            <button
              onClick={() => setActiveTab("insight")}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm
                ${
                  activeTab === "insight"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }
              `}
            >
              Insight Analysis
            </button>
          </nav>
        </div>

        {/* Analysis Content */}
        <div className="mt-6">
          {activeTab === "quality" ? (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Data Quality Analysis</h2>
                <button
                  onClick={handleStartQuality}
                  disabled={isQualityStarting}
                  className={`px-4 py-2 ${
                    isQualityStarting
                      ? "bg-gray-400"
                      : "bg-blue-600 hover:bg-blue-700"
                  } text-white rounded-md`}
                >
                  {isQualityStarting ? "Starting..." : "Start Analysis"}
                </button>
              </div>

              {qualityReport && (
                <div className="bg-white shadow rounded-lg p-6">
                  <h3 className="text-lg font-medium mb-4">Quality Report</h3>
                  <div className="space-y-4">
                    <div>
                      <p>Total Issues: {qualityReport.summary.totalIssues}</p>
                      <p>
                        Critical Issues: {qualityReport.summary.criticalIssues}
                      </p>
                      <p>
                        Warning Issues: {qualityReport.summary.warningIssues}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Data Insight Analysis</h2>
                <button
                  onClick={handleStartInsight}
                  disabled={isInsightStarting}
                  className={`px-4 py-2 ${
                    isInsightStarting
                      ? "bg-gray-400"
                      : "bg-blue-600 hover:bg-blue-700"
                  } text-white rounded-md`}
                >
                  {isInsightStarting ? "Starting..." : "Start Analysis"}
                </button>
              </div>

              {insightReport && (
                <div className="bg-white shadow rounded-lg p-6">
                  <h3 className="text-lg font-medium mb-4">Insight Report</h3>
                  <div className="space-y-4">
                    <div>
                      <p>
                        Patterns Found: {insightReport.summary.patternsFound}
                      </p>
                      <p>
                        Anomalies Detected:{" "}
                        {insightReport.summary.anomaliesDetected}
                      </p>
                      <p>
                        Correlations:{" "}
                        {insightReport.summary.correlationsIdentified}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};
