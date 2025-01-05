// src/common/utils/routeProcessor.tsx
import React, { Suspense } from "react";
import { RouteObject } from "react-router-dom";
import { ErrorBoundary } from "@/common/components/errors/ErrorBoundary";
import { LoadingSpinner } from "@/common/components/navigation/LoadingSpinner";
import type { RouteConfig } from "../types/routes";

const createElementWithWrappers = (
  routeConfig: RouteConfig
): React.ReactNode => {
  let element: React.ReactNode = (
    <ErrorBoundary>
      <Suspense fallback={<LoadingSpinner />}>
        {React.createElement(routeConfig.element)}
      </Suspense>
    </ErrorBoundary>
  );

  // Wrap with guard if specified
  if (routeConfig.guard) {
    const { component: Guard, props: guardProps } = routeConfig.guard;
    element = <Guard {...guardProps}>{element}</Guard>;
  }

  // Wrap with layout if specified
  if (routeConfig.layoutComponent) {
    const Layout = routeConfig.layoutComponent;
    element = <Layout>{element}</Layout>;
  }

  return element;
};

const transformToRouteObject = (routeConfig: RouteConfig): RouteObject => {
  const element = createElementWithWrappers(routeConfig);

  const route: RouteObject = {
    path: routeConfig.path,
    element,
    index: routeConfig.index,
    caseSensitive: routeConfig.caseSensitive,
  };

  // Recursively process children if they exist
  if (routeConfig.children) {
    route.children = routeConfig.children.map(transformToRouteObject);
  }

  return route;
};

export const processRoutes = (routes: RouteConfig[]): RouteObject[] => {
  return routes.map(transformToRouteObject);
};
