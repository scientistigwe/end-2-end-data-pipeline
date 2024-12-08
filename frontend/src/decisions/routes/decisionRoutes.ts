// src/decisions/routes/decisionRoutes.ts
import { lazy } from 'react';
import { RouteConfig } from '../../common/types/routes';

const DecisionsPage = lazy(() => 
  import('../pages/DecisionsPage').then(module => ({ default: module.default }))
);

const DecisionDetails = lazy(() => 
  import('../components/DecisionDetails').then(module => ({ default: module.DecisionDetails }))
);

export const decisionRoutes: RouteConfig[] = [
  {
    path: '/decisions',
    element: DecisionsPage,
    role: 'user',
    children: [
      {
        path: ':id',
        element: DecisionDetails,
      }
    ]
  }
];

// Make sure to export routes index
export default decisionRoutes;