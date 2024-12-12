// src/monitoring/routes/monitoringRoutes.ts
import { lazy } from 'react';
import type { RouteConfig } from '../../common/types/routes';

const MonitoringPage = lazy(() => import('../pages/MonitoringPage'));
const MonitoringDetailsPage = lazy(() => import('../pages/MonitoringDetailsPage'));

export const monitoringRoutes: RouteConfig[] = [
  {
    path: '/monitoring',
    element: MonitoringPage,
    role: 'user',
    children: [
      {
        path: ':pipelineId',
        element: MonitoringDetailsPage
      }
    ]
  }
];

