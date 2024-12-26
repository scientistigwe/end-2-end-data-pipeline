// src/common/api/routes.ts

export const APIRoutes = {
  AUTH: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    REFRESH: '/auth/refresh',
    LOGOUT: '/auth/logout',
    VERIFY: '/auth/verify',
    FORGOT_PASSWORD: '/auth/forgot-password',
    RESET_PASSWORD: '/auth/reset-password',
    VERIFY_EMAIL: '/auth/verify-email',
    PROFILE: '/auth/profile',
    CHANGE_PASSWORD: '/auth/change-password'
  },

  DATA_SOURCES: {
    LIST: '/sources',
    CREATE: '/sources',
    GET: '/sources/:source_id',
    UPDATE: '/sources/:source_id',
    DELETE: '/sources/:source_id',
    TEST: '/sources/:source_id/test',
    SYNC: '/sources/:source_id/sync',
    VALIDATE: '/sources/:source_id/validate',
    PREVIEW: '/sources/:source_id/preview',
    DISCONNECT: '/sources/connection/:connection_id/disconnect',
    STATUS: '/sources/connection/:connection_id/status',

    API: {
      CONNECT: '/sources/api/connect',
      TEST: '/sources/api/test-endpoint',
      EXECUTE: '/sources/api/:connection_id/execute',
      STATUS: '/sources/api/:connection_id/status',
      METADATA: '/sources/api/metadata'
    },

    DATABASE: {
      CONNECT: '/sources/database/connect',
      TEST: '/sources/database/:connection_id/test',
      QUERY: '/sources/database/:connection_id/query',
      SCHEMA: '/sources/database/:connection_id/schema',
      STATUS: '/sources/database/:connection_id/status',
      METADATA: '/sources/database/metadata'
    },

    S3: {
      CONNECT: '/sources/s3/connect',
      LIST: '/sources/s3/:connection_id/list',
      INFO: '/sources/s3/:connection_id/info',
      DOWNLOAD: '/sources/s3/:connection_id/download',
      STATUS: '/sources/s3/:connection_id/status',
      METADATA: '/sources/s3/metadata'
    },

    STREAM: {
      CONNECT: '/sources/stream/connect',
      STATUS: '/sources/stream/:connection_id/status',
      METRICS: '/sources/stream/:connection_id/metrics',
      START: '/sources/stream/start',
      STOP: '/sources/stream/stop',
      METADATA: '/sources/stream/metadata'
    },

    FILE: {
      UPLOAD: '/sources/file/upload',
      PARSE: '/sources/file/:file_id/parse',
      METADATA: '/sources/file/:file_id/metadata'
    }
  },

  PIPELINES: {
    LIST: '/pipelines',
    CREATE: '/pipelines',
    GET: '/pipelines/:pipeline_id',
    UPDATE: '/pipelines/:pipeline_id',
    DELETE: '/pipelines/:pipeline_id',
    START: '/pipelines/:pipeline_id/start',
    STOP: '/pipelines/:pipeline_id/stop',
    STATUS: '/pipelines/:pipeline_id/status',
    LOGS: '/pipelines/:pipeline_id/logs',
    PAUSE: '/pipelines/:pipeline_id/pause',
    RESUME: '/pipelines/:pipeline_id/resume',
    RETRY: '/pipelines/:pipeline_id/retry',
    METRICS: '/pipelines/:pipeline_id/metrics',
    RUNS: '/pipelines/runs',
    VALIDATE: '/pipelines/validate'
  },

  ANALYSIS: {
    QUALITY: {
      START: '/analysis/quality/start',
      STATUS: '/analysis/quality/:analysis_id/status',
      REPORT: '/analysis/quality/:analysis_id/report',
      EXPORT: '/analysis/quality/:analysis_id/export'
    },
    INSIGHT: {
      START: '/analysis/insight/start',
      STATUS: '/analysis/insight/:analysis_id/status',
      REPORT: '/analysis/insight/:analysis_id/report',
      TRENDS: '/analysis/insight/:analysis_id/trends',
      PATTERN_DETAILS: '/analysis/insight/:analysis_id/pattern/:pattern_id',
      EXPORT: '/analysis/insight/:analysis_id/export',
      CORRELATIONS: '/analysis/insight/:analysis_id/correlations',
      ANOMALIES: '/analysis/insight/:analysis_id/anomalies'
    },
    UPLOAD: '/analysis/upload',
    CANCEL: '/analysis/:analysis_id/cancel'
  },

  MONITORING: {
    START: '/monitoring/:pipeline_id/start',
    METRICS: '/monitoring/:pipeline_id/metrics',
    HEALTH: '/monitoring/:pipeline_id/health',
    PERFORMANCE: '/monitoring/:pipeline_id/performance',
    ALERTS_CONFIG: '/monitoring/:pipeline_id/alerts/config',
    ALERTS_HISTORY: '/monitoring/:pipeline_id/alerts/history',
    RESOURCES: '/monitoring/:pipeline_id/resources',
    TIME_SERIES: '/monitoring/:pipeline_id/time-series',
    AGGREGATED: '/monitoring/:pipeline_id/metrics/aggregated'
  },

  REPORTS: {
    LIST: '/reports',
    CREATE: '/reports',
    GET: '/reports/:report_id',
    UPDATE: '/reports/:report_id',
    DELETE: '/reports/:report_id',
    STATUS: '/reports/:report_id/status',
    EXPORT: '/reports/:report_id/export',
    SCHEDULE: '/reports/schedule',
    METADATA: '/reports/:report_id/metadata',
    PREVIEW: '/reports/:report_id/preview',
    TEMPLATES: '/reports/templates'
  },

  RECOMMENDATIONS: {
    LIST: '/recommendations',
    GET: '/recommendations/:recommendation_id',
    APPLY: '/recommendations/:recommendation_id/apply',
    STATUS: '/recommendations/:recommendation_id/status',
    DISMISS: '/recommendations/:recommendation_id/dismiss',
    HISTORY: '/recommendations/pipeline/:pipeline_id/history'
  },

  DECISIONS: {
    LIST: '/decisions',
    GET: '/decisions/:decision_id',
    MAKE: '/decisions/:decision_id/make',
    DEFER: '/decisions/:decision_id/defer',
    HISTORY: '/decisions/pipeline/:pipeline_id/history',
    ANALYZE_IMPACT: '/decisions/:decision_id/options/:option_id/impact',
    LOCK: '/decisions/:decision_id/lock',
    STATE: '/decisions/:decision_id/state',
    UPDATE: '/decisions/:decision_id', 
    COMMENT: '/decisions/:decision_id/comments',
    DELETE: '/decisions/:decision_id'
  },

  SETTINGS: {
    PROFILE: '/settings/profile',
    PREFERENCES: '/settings/preferences',
    SECURITY: '/settings/security',
    NOTIFICATIONS: '/settings/notifications',
    APPEARANCE: '/settings/appearance',
    VALIDATE: '/settings/validate',
    RESET: '/settings/reset'
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