// src/report/pages/ScheduledReportsPage.tsx
import React from "react";
import { Card } from "@/common/components/ui/card";
import { ReportBreadcrumbs } from "../components/ReportBreadcrumbs";
import { useReport } from "../hooks/useReport";
import { getStatusBadgeClass } from "../utils/formatters";
import { dateUtils } from "@/common";

const ScheduledReportsPage: React.FC = () => {
  const { reports, isLoading } = useReport();

  const scheduledReports = reports?.filter(
    (report) => report.config.schedule?.enabled
  );

  return (
    <div className="space-y-6 p-6">
      <ReportBreadcrumbs />

      <div className="grid gap-4">
        {scheduledReports?.map((report) => (
          <Card key={report.id} className="p-4">
            <div className="flex justify-between items-start">
              <div className="space-y-1">
                <h3 className="text-lg font-medium">{report.config.name}</h3>
                <p className="text-sm text-gray-500">
                  Frequency: {report.config.schedule?.frequency}
                </p>
                <p className="text-sm text-gray-500">
                  Next Run:{" "}
                  {dateUtils.formatDate(report.config.schedule?.nextRunAt!, {
                    includeTime: true,
                  })}
                </p>
              </div>

              <div
                className={`px-2 py-1 rounded-full text-sm ${getStatusBadgeClass(
                  report.status
                )}`}
              >
                {report.status}
              </div>
            </div>
          </Card>
        ))}

        {isLoading && <div>Loading scheduled reports...</div>}

        {!isLoading && (!scheduledReports || scheduledReports.length === 0) && (
          <div className="text-center py-8 text-gray-500">
            No scheduled reports found
          </div>
        )}
      </div>
    </div>
  );
};

export default ScheduledReportsPage;
