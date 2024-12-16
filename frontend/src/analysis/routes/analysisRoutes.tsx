// src/analysis/routes/analysisRoutes.tsx
import React, { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const AnalysisPage = lazy(() => import("../pages/AnalysisPage"));
const DashboardPage = lazy(() => import("../pages/AnalysisDashboardPage"));

export const analysisRoutes: RouteObject[] = [
  {
    path: "analysis",
    children: [
      {
        index: true,
        element: <AnalysisPage />,
      },
      {
        path: "dashboard",
        element: <DashboardPage />,
      },
      {
        path: ":analysisId",
        element: <AnalysisPage />,
      },
    ],
  },
];
