// src/pipeline/routes/pipelineRoutes.ts
import { RouteObject } from 'react-router-dom';
import { lazy } from 'react';
import { PipelineGuard } from '../components/PipelineGuard';

// Lazy load pages
const PipelinesPage = lazy(() => import('../pages/PipelinesPage'));
const DashboardPage = lazy(() => import('../pages/DashboardPage'));
const PipelineDetailsPage = lazy(() => import('../pages/PipelineDetailsPage'));
const PipelineRunsPage = lazy(() => import('../pages/PipelineRunsPage'));
const PipelineMetricsPage = lazy(() => import('../pages/PipelineMetricsPage'));

export const PIPELINE_ROUTES = {
  DASHBOARD: '/pipelines/dashboard',
  LIST: '/pipelines',
  DETAILS: '/pipelines/:id',
  RUNS: '/pipelines/:id/runs',
  METRICS: '/pipelines/:id/metrics',
} as const;

export const pipelineRoutes: RouteObject[] = [
  {
    path: 'pipelines',
    element: <PipelineGuard />,
    children: [
      {
        path: 'dashboard',
        element: <DashboardPage />
      },
      {
        path: '',
        element: <PipelinesPage />
      },
      {
        path: ':id',
        children: [
          {
            path: '',
            element: <PipelineDetailsPage />
          },
          {
            path: 'runs',
            element: <PipelineRunsPage />
          },
          {
            path: 'metrics',
            element: <PipelineMetricsPage />
          }
        ]
      }
    ]
  }
];




