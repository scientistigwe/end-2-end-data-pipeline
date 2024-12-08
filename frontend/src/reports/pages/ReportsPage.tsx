// src/pages/ReportsPage.tsx
import React, { useState } from "react";
import { useReport } from "../hooks/useReports";
import type { ReportType } from "../../../../types";
import { formatDate } from "../../common/utils/date/dateUtils";

export const ReportsPage: React.FC = () => {
  const [reportType, setReportType] = useState<ReportType>("quality");

  const { generateReport, reportData, reportHistory, isGenerating, error } =
    useReport("pipeline-123"); // Replace with actual pipeline ID

  const handleGenerateReport = () => {
    generateReport({
      type: reportType,
      timeRange: {
        start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
        end: new Date().toISOString(),
      },
    });
  };

  return (
    <div className="space-y-6">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Reports</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* Report Generation */}
        <section className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Generate Report</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Report Type
              </label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value as ReportType)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="quality">Quality Report</option>
                <option value="insight">Insight Report</option>
                <option value="performance">Performance Report</option>
              </select>
            </div>

            <button
              onClick={handleGenerateReport}
              disabled={isGenerating}
              className={`px-4 py-2 text-white rounded-md ${
                isGenerating
                  ? "bg-gray-400 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700"
              }`}
            >
              {isGenerating ? "Generating..." : "Generate Report"}
            </button>
          </div>

          {error && <div className="mt-4 text-red-600">{error.message}</div>}
        </section>

        {/* Report Display */}
        {reportData && (
          <section className="mt-8 bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Report Results</h2>
            <div className="prose max-w-none">
              {/* Add report content rendering logic here */}
            </div>
          </section>
        )}

        {/* Report History */}
        <section className="mt-8">
          <h2 className="text-xl font-semibold mb-4">Report History</h2>
          <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Report Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Generated At
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {reportHistory?.map((report) => (
                  <tr key={report.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {report.type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {formatDate(report.generatedAt)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          report.status === "completed"
                            ? "bg-green-100 text-green-800"
                            : report.status === "failed"
                            ? "bg-red-100 text-red-800"
                            : "bg-yellow-100 text-yellow-800"
                        }`}
                      >
                        {report.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {/* Add action buttons */}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
};
