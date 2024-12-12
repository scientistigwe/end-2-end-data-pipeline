// src/report/components/ReportBreadcrumbs.tsx
import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { useReport } from '../hooks/useReport';
import { REPORT_ROUTES } from '../routes/reportRoutes';

export const ReportBreadcrumbs: React.FC = () => {
  const { id } = useParams();
  const { report } = useReport(id);

  return (
    <nav className="flex items-center space-x-2 text-sm">
      <Link 
        to={REPORT_ROUTES.LIST}
        className="text-gray-600 hover:text-gray-900"
      >
        Reports
      </Link>

      {id && (
        <>
          <ChevronRight className="h-4 w-4 text-gray-400" />
          <span className="text-gray-900">
            {report?.config.name || 'Report Details'}
          </span>
        </>
      )}

      {window.location.pathname === REPORT_ROUTES.GENERATE && (
        <>
          <ChevronRight className="h-4 w-4 text-gray-400" />
          <span className="text-gray-900">Generate Report</span>
        </>
      )}

      {window.location.pathname === REPORT_ROUTES.SCHEDULED && (
        <>
          <ChevronRight className="h-4 w-4 text-gray-400" />
          <span className="text-gray-900">Scheduled Reports</span>
        </>
      )}
    </nav>
  );
};
