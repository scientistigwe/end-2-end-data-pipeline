// src/reports/routes/reportRoutes.ts
import { RouteObject } from 'react-router-dom';

// Type definitions for route paths and keys
export type ReportRouteType = typeof REPORT_ROUTES[keyof typeof REPORT_ROUTES];
export type ReportRouteKey = keyof typeof REPORT_ROUTES;

// Route path constants
export const REPORT_ROUTES = {
  LIST: '/reports' as '/reports',
  DETAILS: '/reports/:id' as '/reports/:id',
  GENERATE: '/reports/generate' as '/reports/generate',
  SCHEDULED: '/reports/scheduled' as '/reports/scheduled',
} as const;

// Navigation parameter types
export interface ReportNavigationParams {
  DETAILS: { id: string };
  LIST: never;
  GENERATE: never;
  SCHEDULED: never;
}

// Type-safe path generation helper
export const getReportPath = <T extends ReportRouteKey>(
  path: T,
  params?: Record<string, string>
): string => {
  let routePath = REPORT_ROUTES[path];

  if (!params) {
    return routePath;
  }

  return Object.entries(params).reduce(
    (acc: string, [key, value]) => acc.replace(`:${key}`, value),
    routePath
  );
};

// Route configuration
const routes: RouteObject[] = [
  {
    path: 'reports',
    async lazy() {
      const { ReportsGuard } = await import('../components/ReportsGuard');
      return { Component: ReportsGuard };
    },
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

export default routes;