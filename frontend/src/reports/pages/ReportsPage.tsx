// src/report/pages/ReportsPage.tsx
import React, { useState } from "react";
import { Button } from "@/common/components/ui/button";
import { Input } from "@/common/components/ui/inputs/input";
import { Select } from "@/common/components/ui/inputs/select";
import { ReportList } from "../components/ReportList";
import { ReportBreadcrumbs } from "../components/ReportBreadcrumbs";
import { useReport } from "../hooks/useReport";
import { useReportNavigation } from "../routes/navigationUtils";
import { REPORT_CONSTANTS } from "../constants";
import type { ReportType, ReportStatus } from "../types/models";

const ReportsPage: React.FC = () => {
  const { reports, isLoading, exportReport, deleteReport } = useReport();
  const navigation = useReportNavigation();
  const [filters, setFilters] = useState({
    type: "",
    status: "",
    search: "",
  });

  const filteredReports = reports?.filter((report) => {
    if (filters.type && report.config.type !== filters.type) return false;
    if (filters.status && report.status !== filters.status) return false;
    if (
      filters.search &&
      !report.config.name.toLowerCase().includes(filters.search.toLowerCase())
    )
      return false;
    return true;
  });

  return (
    <div className="space-y-6 p-6">
      <div className="flex justify-between items-center">
        <ReportBreadcrumbs />
        <Button onClick={() => navigation.goToReportGeneration()}>
          Generate Report
        </Button>
      </div>

      <div className="flex space-x-4">
        <Input
          placeholder="Search reports..."
          value={filters.search}
          onChange={(e) =>
            setFilters((prev) => ({ ...prev, search: e.target.value }))
          }
          className="max-w-xs"
        />
        <Select
          value={filters.type}
          onChange={(e) =>
            setFilters((prev) => ({ ...prev, type: e.target.value }))
          }
        >
          <option value="">All Types</option>
          {Object.values(REPORT_CONSTANTS.TYPES).map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </Select>
        <Select
          value={filters.status}
          onChange={(e) =>
            setFilters((prev) => ({ ...prev, status: e.target.value }))
          }
        >
          <option value="">All Status</option>
          {Object.values(REPORT_CONSTANTS.STATUS).map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </Select>
      </div>

      <ReportList
        reports={filteredReports || []}
        onExport={exportReport}
        onDelete={deleteReport}
        onSchedule={(id) => navigation.goToReportDetails(id)}
        isLoading={isLoading}
      />
    </div>
  );
};

export default ReportsPage;
