// src/recommendations/routes/recommendationRoutes.ts
import { lazy } from 'react';
import type { RouteConfig } from '../../common/types/routes';

const RecommendationsPage = lazy(() => import('../pages/RecommendationsPage'));

export const recommendationRoutes: RouteConfig[] = [
  {
    path: '/recommendations',
    element: RecommendationsPage,
    role: 'user'
  }
];

export default recommendationRoutes;
