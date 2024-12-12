// src/report/hooks/useReportNavigation.ts
import { useNavigate } from 'react-router-dom';
import { REPORT_ROUTES, getReportPath } from '../routes/reportRoutes';

export const useReportNavigation = () => {
  const navigate = useNavigate();

  return {
    goToReportsList: () => navigate(REPORT_ROUTES.LIST),
    goToReportDetails: (id: string) => navigate(getReportPath('DETAILS', { id })),
    goToReportGeneration: () => navigate(REPORT_ROUTES.GENERATE),
    goToScheduledReports: () => navigate(REPORT_ROUTES.SCHEDULED),
    openReportInNewTab: (id: string) => {
      window.open(getReportPath('DETAILS', { id }), '_blank');
    }
  };
};