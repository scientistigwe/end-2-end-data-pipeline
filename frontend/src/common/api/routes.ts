// src/common/api/routes.ts

export const APIRoutes = {
  AUTH: {
    LOGIN: '/api/v1/auth/login',
    REGISTER: '/api/v1/auth/register',
    REFRESH: '/api/v1/auth/refresh',
    LOGOUT: '/api/v1/auth/logout',
    VERIFY: '/api/v1/auth/verify',
    FORGOT_PASSWORD: '/api/v1/auth/forgot-password',
    RESET_PASSWORD: '/api/v1/auth/reset-password',
    VERIFY_EMAIL: '/api/v1/auth/verify-email',
    PROFILE: '/api/v1/auth/profile',
    CHANGE_PASSWORD: '/api/v1/auth/change-password'
  },

  DATA_SOURCES: {
    LIST: '/api/v1/sources',
    CREATE: '/api/v1/sources',
    GET: '/api/v1/sources/:source_id',
    UPDATE: '/api/v1/sources/:source_id',
    DELETE: '/api/v1/sources/:source_id',
    TEST: '/api/v1/sources/:source_id/test',
    SYNC: '/api/v1/sources/:source_id/sync',
    VALIDATE: '/api/v1/sources/:source_id/validate',
    PREVIEW: '/api/v1/sources/:source_id/preview',
    DISCONNECT: '/api/v1/sources/connection/:connection_id/disconnect',
    STATUS: '/api/v1/sources/connection/:connection_id/status',

    API: {
      CONNECT: '/api/v1/sources/api/connect',
      TEST: '/api/v1/sources/api/test-endpoint',
      EXECUTE: '/api/v1/sources/api/:connection_id/execute',
      STATUS: '/api/v1/sources/api/:connection_id/status',
      METADATA: '/api/v1/sources/api/metadata'
    },

    DATABASE: {
      CONNECT: '/api/v1/sources/database/connect',
      TEST: '/api/v1/sources/database/:connection_id/test',
      QUERY: '/api/v1/sources/database/:connection_id/query',
      SCHEMA: '/api/v1/sources/database/:connection_id/schema',
      STATUS: '/api/v1/sources/database/:connection_id/status',
      METADATA: '/api/v1/sources/database/metadata'
    },

    S3: {
      CONNECT: '/api/v1/sources/s3/connect',
      LIST: '/api/v1/sources/s3/:connection_id/list',
      INFO: '/api/v1/sources/s3/:connection_id/info',
      DOWNLOAD: '/api/v1/sources/s3/:connection_id/download',
      STATUS: '/api/v1/sources/s3/:connection_id/status',
      METADATA: '/api/v1/sources/s3/metadata'
    },

    STREAM: {
      CONNECT: '/api/v1/sources/stream/connect',
      STATUS: '/api/v1/sources/stream/:connection_id/status',
      METRICS: '/api/v1/sources/stream/:connection_id/metrics',
      START: '/api/v1/sources/stream/start',
      STOP: '/api/v1/sources/stream/stop',
      METADATA: '/api/v1/sources/stream/metadata'
    },

    FILE: {
      UPLOAD: '/api/v1/sources/file/upload',
      PARSE: '/api/v1/sources/file/:file_id/parse',
      METADATA: '/api/v1/sources/file/:file_id/metadata'
    }
  },

  PIPELINES: {
    LIST: '/api/v1/pipelines',
    CREATE: '/api/v1/pipelines',
    GET: '/api/v1/pipelines/:pipeline_id',
    UPDATE: '/api/v1/pipelines/:pipeline_id',
    DELETE: '/api/v1/pipelines/:pipeline_id',
    START: '/api/v1/pipelines/:pipeline_id/start',
    STOP: '/api/v1/pipelines/:pipeline_id/stop',
    STATUS: '/api/v1/pipelines/:pipeline_id/status',
    LOGS: '/api/v1/pipelines/:pipeline_id/logs',
    PAUSE: '/api/v1/pipelines/:pipeline_id/pause',
    RESUME: '/api/v1/pipelines/:pipeline_id/resume',
    RETRY: '/api/v1/pipelines/:pipeline_id/retry',
    METRICS: '/api/v1/pipelines/:pipeline_id/metrics',
    RUNS: '/api/v1/pipelines/runs',
    VALIDATE: '/api/v1/pipelines/validate'
  },

  ANALYSIS: {
    QUALITY: {
      START: '/api/v1/analysis/quality/start',
      STATUS: '/api/v1/analysis/quality/:analysis_id/status',
      REPORT: '/api/v1/analysis/quality/:analysis_id/report',
      EXPORT: '/api/v1/analysis/quality/:analysis_id/export'
    },
    INSIGHT: {
      START: '/api/v1/analysis/insight/start',
      STATUS: '/api/v1/analysis/insight/:analysis_id/status',
      REPORT: '/api/v1/analysis/insight/:analysis_id/report',
      TRENDS: '/api/v1/analysis/insight/:analysis_id/trends',
      PATTERN_DETAILS: '/api/v1/analysis/insight/:analysis_id/pattern/:pattern_id',
      EXPORT: '/api/v1/analysis/insight/:analysis_id/export',
      CORRELATIONS: '/api/v1/analysis/insight/:analysis_id/correlations',
      ANOMALIES: '/api/v1/analysis/insight/:analysis_id/anomalies'
    },
    UPLOAD: '/api/v1/analysis/upload',
    CANCEL: '/api/v1/analysis/:analysis_id/cancel'
  },

  MONITORING: {
    START: '/api/v1/monitoring/:pipeline_id/start',
    METRICS: '/api/v1/monitoring/:pipeline_id/metrics',
    HEALTH: '/api/v1/monitoring/:pipeline_id/health',
    PERFORMANCE: '/api/v1/monitoring/:pipeline_id/performance',
    ALERTS_CONFIG: '/api/v1/monitoring/:pipeline_id/alerts/config',
    ALERTS_HISTORY: '/api/v1/monitoring/:pipeline_id/alerts/history',
    RESOURCES: '/api/v1/monitoring/:pipeline_id/resources',
    TIME_SERIES: '/api/v1/monitoring/:pipeline_id/time-series',
    AGGREGATED: '/api/v1/monitoring/:pipeline_id/metrics/aggregated'
  },

  REPORTS: {
    LIST: '/api/v1/reports',
    CREATE: '/api/v1/reports',
    GET: '/api/v1/reports/:report_id',
    UPDATE: '/api/v1/reports/:report_id',
    DELETE: '/api/v1/reports/:report_id',
    STATUS: '/api/v1/reports/:report_id/status',
    EXPORT: '/api/v1/reports/:report_id/export',
    SCHEDULE: '/api/v1/reports/schedule',
    METADATA: '/api/v1/reports/:report_id/metadata',
    PREVIEW: '/api/v1/reports/:report_id/preview',
    TEMPLATES: '/api/v1/reports/templates'
  },

  RECOMMENDATIONS: {
    LIST: '/api/v1/recommendations',
    GET: '/api/v1/recommendations/:recommendation_id',
    APPLY: '/api/v1/recommendations/:recommendation_id/apply',
    STATUS: '/api/v1/recommendations/:recommendation_id/status',
    DISMISS: '/api/v1/recommendations/:recommendation_id/dismiss',
    HISTORY: '/api/v1/recommendations/pipeline/:pipeline_id/history'
  },

  DECISIONS: {
    LIST: '/api/v1/decisions',
    GET: '/api/v1/decisions/:decision_id',
    MAKE: '/api/v1/decisions/:decision_id/make',
    DEFER: '/api/v1/decisions/:decision_id/defer',
    HISTORY: '/api/v1/decisions/pipeline/:pipeline_id/history',
    ANALYZE_IMPACT: '/api/v1/decisions/:decision_id/options/:option_id/impact',
    LOCK: '/api/v1/decisions/:decision_id/lock',
    STATE: '/api/v1/decisions/:decision_id/state'
  },

  SETTINGS: {
    PROFILE: '/api/v1/settings/profile',
    PREFERENCES: '/api/v1/settings/preferences',
    SECURITY: '/api/v1/settings/security',
    NOTIFICATIONS: '/api/v1/settings/notifications',
    APPEARANCE: '/api/v1/settings/appearance',
    VALIDATE: '/api/v1/settings/validate',
    RESET: '/api/v1/settings/reset'
  }
} as const;

  // Type definitions
  // Basic route types
  export type RouteKey = keyof typeof APIRoutes;
  export type RouteParams = Record<string, string | number>;
  
  // Helper type to check if a type is a nested route object
  type IsNestedRoute<T> = T extends { [key: string]: string } ? true : false;
  
  // Get direct route keys
  export type SubRouteKey<T extends RouteKey> = {
    [K in keyof typeof APIRoutes[T]]: typeof APIRoutes[T][K] extends string ? K : never;
  }[keyof typeof APIRoutes[T]];
  
  // Get nested route keys
  export type NestedRouteKey<
    T extends RouteKey,
    S extends keyof typeof APIRoutes[T]
  > = typeof APIRoutes[T][S] extends { [key: string]: string }
    ? keyof typeof APIRoutes[T][S]
    : never;
  
  // Helper function to check if a route is nested
  function isNestedRouteSection<T extends RouteKey>(
    routes: typeof APIRoutes[T],
    section: keyof typeof routes
  ): boolean {
    return typeof routes[section] === 'object' && !Array.isArray(routes[section]);
  }
  
  // Route formatting function
  function formatRouteWithParams(route: string, params?: RouteParams): string {
    if (!params) return route;
    
    return Object.entries(params).reduce(
      (formattedRoute, [key, value]) => 
        formattedRoute.replace(`:${key}`, encodeURIComponent(String(value))),
      route
    );
  }
  
  // Route helpers with proper typing
  export const RouteHelper = {
    // For simple routes
    getRoute<T extends RouteKey>(
      module: T,
      route: SubRouteKey<T>,
      params?: RouteParams
    ): string {
      const moduleRoutes = APIRoutes[module];
      const baseRoute = moduleRoutes[route as keyof typeof moduleRoutes];
      
      if (typeof baseRoute !== 'string') {
        throw new Error(`Invalid route: ${String(route)} in module ${String(module)}`);
      }
      
      return formatRouteWithParams(baseRoute, params);
    },
  
    // For nested routes
    getNestedRoute<
      T extends RouteKey,
      S extends keyof typeof APIRoutes[T],
      R extends NestedRouteKey<T, S>
    >(
      module: T,
      section: S,
      route: R,
      params?: RouteParams
    ): string {
      const moduleRoutes = APIRoutes[module];
      const sectionRoutes = moduleRoutes[section];
      
      if (!isNestedRouteSection(moduleRoutes, section)) {
        throw new Error(`Invalid section: ${String(section)} in module ${String(module)}`);
      }
      
      const baseRoute = (sectionRoutes as Record<string, string>)[route as string];
      if (typeof baseRoute !== 'string') {
        throw new Error(`Invalid route: ${String(route)} in section ${String(section)}`);
      }
      
      return formatRouteWithParams(baseRoute, params);
    }
  };
  
  // Type for unified route configuration
  export type RouteConfig<
    T extends RouteKey,
    S extends keyof typeof APIRoutes[T] = never,
    R extends S extends never ? never : NestedRouteKey<T, S> = never
  > = {
    module: T;
    section?: S;
    route: S extends never ? SubRouteKey<T> : R;
    params?: RouteParams;
  };
  
  // Utility function to create route configuration
  export function createRouteConfig<
    T extends RouteKey,
    S extends keyof typeof APIRoutes[T] = never,
    R extends S extends never ? never : NestedRouteKey<T, S> = never
  >(config: RouteConfig<T, S, R>): RouteConfig<T, S, R> {
    return config;
  }
  
  // Usage example in a type-safe way
  export function getRoutePath<
    T extends RouteKey,
    S extends keyof typeof APIRoutes[T] = never,
    R extends S extends never ? never : NestedRouteKey<T, S> = never
  >(config: RouteConfig<T, S, R>): string {
    if (config.section) {
      return RouteHelper.getNestedRoute(
        config.module,
        config.section,
        config.route as NestedRouteKey<T, S>,
        config.params
      );
    }
    return RouteHelper.getRoute(
      config.module,
      config.route as SubRouteKey<T>,
      config.params
    );
  }