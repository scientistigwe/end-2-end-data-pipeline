// src/report/routes/reportRoutes.ts
import { RouteObject } from 'react-router-dom';
import { lazy } from 'react';
import { ReportsGuard } from '../components/ReportsGuard';

// Simple route paths object
export const REPORT_PATHS = {
  LIST: '/reports',
  DETAILS: '/reports/:id',
  GENERATE: '/reports/generate',
  SCHEDULED: '/reports/scheduled',
} as const;

// Basic route configuration
const routes: RouteObject[] = [
  {
    path: 'reports',
    element: <ReportsGuard />,
    children: [
      {
        path: '',
        async lazy() {
          const { ReportsPage } = await import('../pages/ReportsPage');
          return { Component: ReportsPage };
        },
      },
      {
        path: 'generate',
        async lazy() {
          const { ReportGenerationPage } = await import('../pages/ReportGenerationPage');
          return { Component: ReportGenerationPage };
        },
      },
      {
        path: 'scheduled',
        async lazy() {
          const { ScheduledReportsPage } = await import('../pages/ScheduledReportsPage');
          return { Component: ScheduledReportsPage };
        },
      },
      {
        path: ':id',
        async lazy() {
          const { ReportDetailsPage } = await import('../pages/ReportDetailsPage');
          return { Component: ReportDetailsPage };
        },
      },
    ],
  },
];

// Simple navigation helper
export const getReportPath = (
  path: keyof typeof REPORT_PATHS,
  params?: Record<string, string>
): string => {
  let routePath = REPORT_PATHS[path];
  
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      routePath = routePath.replace(`:${key}`, value);
    });
  }
  
  return routePath;
};

export default routes;