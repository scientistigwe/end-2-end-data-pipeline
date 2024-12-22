// src/common/utils/routeProcessor.tsx
import React, { Suspense } from 'react';
import { RouteObject } from 'react-router-dom';
import { ErrorBoundary } from '@/common/components/errors/ErrorBoundary';
import { LoadingSpinner } from '@/common/components/navigation/LoadingSpinner';
import type { RouteConfig } from '../types/routes';

export const processRouteConfig = (config: RouteConfig): RouteObject => {
  let element = (
    <ErrorBoundary>
      <Suspense fallback={<LoadingSpinner />}>
        <config.element />
      </Suspense>
    </ErrorBoundary>
  );

  // Apply guard if specified
  if (config.guard) {
    const Guard = config.guard.component;
    element = <Guard {...config.guard.props}>{element}</Guard>;
  }

  // Apply layout if specified
  if (config.layoutComponent) {
    const Layout = config.layoutComponent;
    element = <Layout>{element}</Layout>;
  }

  const route: RouteObject = {
    path: config.path,
    element: element,
    index: config.index,
    caseSensitive: config.caseSensitive,
  };

  // Process children if they exist
  if (config.children) {
    route.children = config.children.map(processRouteConfig);
  }

  return route;
};

export const processRoutes = (routes: RouteConfig[]): RouteObject[] => {
  return routes.map(processRouteConfig);
};