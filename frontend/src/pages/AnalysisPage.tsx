// src/pages/AnalysisPage.tsx
import React, { useState } from "react";
import { useQualityAnalysis } from "../hooks/analytics/useQualityAnalysis";
import { useInsightAnalysis } from "../hooks/analytics/useQualityAnalysis";

export const AnalysisPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"quality" | "insight">("quality");
  const { startAnalysis: startQuality, report: qualityReport } =
    useQualityAnalysis("quality");
  const { startAnalysis: startInsight, report: insightReport } =
    useInsightAnalysis("insight");

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
                  onClick={() => startQuality()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Start Analysis
                </button>
              </div>

              {qualityReport && (
                <div className="bg-white shadow rounded-lg p-6">
                  {/* Quality report content */}
                </div>
              )}
            </div>
          ) : (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Data Insight Analysis</h2>
                <button
                  onClick={() => startInsight()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Start Analysis
                </button>
              </div>

              {insightReport && (
                <div className="bg-white shadow rounded-lg p-6">
                  {/* Insight report content */}
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};
