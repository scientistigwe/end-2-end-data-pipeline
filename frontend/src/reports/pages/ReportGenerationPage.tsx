// src/report/pages/ReportGenerationPage.tsx
import React from "react";
import { useNavigate } from "react-router-dom";
import { ReportForm } from "../components/ReportForm";
import { ReportBreadcrumbs } from "../components/ReportBreadcrumbs";
import { useReport } from "../hooks/useReport";
import type { ReportConfig } from "../types/report";

const ReportGenerationPage: React.FC = () => {
  const navigate = useNavigate();
  const { createReport, isLoading } = useReport();

  const handleSubmit = async (config: ReportConfig) => {
    try {
      const report = await createReport(config);
      navigate(`/reports/${report.id}`);
    } catch (error) {
      console.error("Failed to create report:", error);
    }
  };

  return (
    <div className="space-y-6 p-6">
      <ReportBreadcrumbs />

      <ReportForm onSubmit={handleSubmit} isLoading={isLoading} />
    </div>
  );
};

export default ReportGenerationPage;
