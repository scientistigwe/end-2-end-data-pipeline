// src/report/pages/ReportDetailsPage.tsx
import React from 'react';
import { useParams } from 'react-router-dom';
import { ReportViewer } from '../components/ReportViewer';
import { ReportBreadcrumbs } from '../components/ReportBreadcrumbs';
import { useReport } from '../hooks/useReport';
import { useReportGeneration } from '../hooks/useReportGeneration';

export const ReportDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { report, isLoading, refreshReport } = useReport(id);
  const { exportReport } = useReportGeneration(id!);

  if (isLoading || !report) {
    return <div>Loading...</div>;
  }

  return (
    <div className="space-y-6 p-6">
      <ReportBreadcrumbs />
      
      <ReportViewer
        report={report}
        onExport={exportReport}
        onRefresh={refreshReport}
      />
    </div>
  );
};
