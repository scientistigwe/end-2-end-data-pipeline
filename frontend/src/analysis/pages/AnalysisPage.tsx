import React, { useState, useEffect } from "react";
import { useAnalysis } from "../hooks/useAnalysis";
import { useAnalysisDetails } from "../hooks/useAnalysisDetails";
import type { QualityConfig, InsightConfig } from "../types/analysis";

export const AnalysisPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"quality" | "insight">("quality");
  const [isStarting, setIsStarting] = useState(false);

  const {
    selectedAnalysis,
    selectedQualityReport,
    selectedInsightReport,
    startQualityAnalysis,
    startInsightAnalysis,
    getQualityReport,
    getInsightReport,
    pollAnalysisStatus
  } = useAnalysis();

  const {
    getCorrelations,
    getAnomalies,
    getTrends
  } = useAnalysisDetails();

  const handleStartQuality = async () => {
    setIsStarting(true);
    try {
      const config: QualityConfig = {
        rules: {
          dataTypes: true,
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
      };

      const analysis = await startQualityAnalysis(config);
      await pollAnalysisStatus(analysis.id);
      await getQualityReport(analysis.id);
    } catch (error) {
      console.error('Failed to start quality analysis:', error);
    } finally {
      setIsStarting(false);
    }
  };

  const handleStartInsight = async () => {
    setIsStarting(true);
    try {
      const config: InsightConfig = {
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
      };

      const analysis = await startInsightAnalysis(config);
      await pollAnalysisStatus(analysis.id);
      await getInsightReport(analysis.id);

      // Fetch additional insight details
      if (analysis.id) {
        await Promise.all([
          getCorrelations(analysis.id),
          getAnomalies(analysis.id),
          getTrends(analysis.id)
        ]);
      }
    } catch (error) {
      console.error('Failed to start insight analysis:', error);
    } finally {
      setIsStarting(false);
    }
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
                ${activeTab === "quality"
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
                ${activeTab === "insight"
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
                  disabled={isStarting}
                  className={`px-4 py-2 ${
                    isStarting
                      ? "bg-gray-400"
                      : "bg-blue-600 hover:bg-blue-700"
                  } text-white rounded-md`}
                >
                  {isStarting ? "Starting..." : "Start Analysis"}
                </button>
              </div>

              {selectedQualityReport && (
                <div className="bg-white shadow rounded-lg p-6">
                  <h3 className="text-lg font-medium mb-4">Quality Report</h3>
                  <div className="space-y-4">
                    <div>
                      <p>Total Issues: {selectedQualityReport.summary.totalIssues}</p>
                      <p>Critical Issues: {selectedQualityReport.summary.criticalIssues}</p>
                      <p>Warning Issues: {selectedQualityReport.summary.warningIssues}</p>
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
                  disabled={isStarting}
                  className={`px-4 py-2 ${
                    isStarting
                      ? "bg-gray-400"
                      : "bg-blue-600 hover:bg-blue-700"
                  } text-white rounded-md`}
                >
                  {isStarting ? "Starting..." : "Start Analysis"}
                </button>
              </div>

              {selectedInsightReport && (
                <div className="bg-white shadow rounded-lg p-6">
                  <h3 className="text-lg font-medium mb-4">Insight Report</h3>
                  <div className="space-y-4">
                    <div>
                      <p>Patterns Found: {selectedInsightReport.summary.patternsFound}</p>
                      <p>Anomalies Detected: {selectedInsightReport.summary.anomaliesDetected}</p>
                      <p>Correlations: {selectedInsightReport.summary.correlationsIdentified}</p>
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