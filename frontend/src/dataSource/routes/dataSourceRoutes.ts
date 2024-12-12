// src/dataSource/routes/dataSourceRoutes.ts
import { lazy } from 'react';
import type { RouteConfig } from '../../common/types/routes';

const DataSourcesPage = lazy(() => import('../pages/DataSourcesPage'));
const DataSourceDetailsPage = lazy(() => import('../pages/DataSourceDetailsPage'));

export const dataSourceRoutes: RouteConfig[] = [
  {
    path: '/data-sources',
    element: DataSourcesPage,
    children: [
      {
        path: ':id',
        element: DataSourceDetailsPage,
      }
    ]
  }
];

// src/dataSource/routes/index.ts
export * from './dataSourceRoutes';