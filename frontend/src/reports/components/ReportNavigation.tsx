// src/report/components/ReportNavigation.tsx
import React from "react";
import { Button } from "@/common/components/ui/button";
import { useReportNavigation } from "../routes/navigationUtils";

interface ReportNavigationProps {
  reportId?: string;
}

export const ReportNavigation: React.FC<ReportNavigationProps> = ({
  reportId,
}) => {
  const navigation = useReportNavigation();

  return (
    <div className="space-x-2">
      <Button
        variant="outline"
        onClick={() => navigation.goToReportGeneration()}
      >
        Generate Report
      </Button>

      <Button
        variant="outline"
        onClick={() => navigation.goToScheduledReports()}
      >
        Scheduled Reports
      </Button>

      {reportId && (
        <Button
          variant="outline"
          onClick={() => navigation.goToReportDetails(reportId)}
        >
          View Details
        </Button>
      )}
    </div>
  );
};
