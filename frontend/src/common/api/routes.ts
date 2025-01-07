// src/dataSource/types/routes.ts
 
import { z } from 'zod';

export enum DataSourceType {
    FILE = 'file',
    DATABASE = 'database',
    API = 'api',
    S3 = 's3',
    STREAM = 'stream'
}

// Route parameter validation schema
export const RouteParamsSchema = z.object({
  source_id: z.string().optional(),
  pipeline_id: z.string().optional(),
  analysis_id: z.string().optional(),
  file_id: z.string().optional(),
  connection_id: z.string().optional(),
  decision_id: z.string().optional(),
  option_id: z.string().optional(),
  pattern_id: z.string().optional(),
  report_id: z.string().optional(),
  recommendation_id: z.string().optional(),
});

export type RouteParams = z.infer<typeof RouteParamsSchema>;

export const APIRoutes = {
  AUTH: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    LOGOUT: '/auth/logout',
    VERIFY: '/auth/verify',
    REFRESH: '/auth/refresh',
    FORGOT_PASSWORD: '/auth/forgot-password',
    RESET_PASSWORD: '/auth/reset-password',
    VERIFY_EMAIL: '/auth/verify-email',
    PROFILE: '/auth/profile',
    CHANGE_PASSWORD: '/auth/change-password'
  },

  DATA_SOURCES: {
    LIST: '/data-sources',
    CREATE: '/data-sources',
    GET: '/data-sources/{source_id}',
    UPDATE: '/data-sources/{source_id}',
    DELETE: '/data-sources/{source_id}',
    TEST: '/data-sources/{source_id}/test',
    SYNC: '/data-sources/{source_id}/sync',
    VALIDATE: '/data-sources/{source_id}/validate',
    PREVIEW: '/data-sources/{source_id}/preview',
    CONNECTION: {
      DISCONNECT: '/data-sources/connection/{connection_id}/disconnect',
      STATUS: '/data-sources/connection/{connection_id}/status'
    },

    FILE: {
      UPLOAD: '/data-sources/file/upload',
      PARSE: '/data-sources/file/{file_id}/parse',
      METADATA: '/data-sources/file/{file_id}/metadata'
    },

    DATABASE: {
      CONNECT: '/data-sources/database/connect',
      TEST: '/data-sources/database/{connection_id}/test',
      QUERY: '/data-sources/database/{connection_id}/query',
      SCHEMA: '/data-sources/database/{connection_id}/schema',
      METADATA: '/data-sources/database/metadata'
    },

    API: {
      CONNECT: '/data-sources/api/connect',
      TEST: '/data-sources/api/test-endpoint',
      EXECUTE: '/data-sources/api/{connection_id}/execute',
      STATUS: '/data-sources/api/{connection_id}/status',
      METADATA: '/data-sources/api/metadata'
    },

    S3: {
      CONNECT: '/data-sources/s3/connect',
      LIST: '/data-sources/s3/{connection_id}/list',
      INFO: '/data-sources/s3/{connection_id}/info',
      DOWNLOAD: '/data-sources/s3/{connection_id}/download',
      METADATA: '/data-sources/s3/metadata'
    },

    STREAM: {
      CONNECT: '/data-sources/stream/connect',
      STATUS: '/data-sources/stream/{connection_id}/status',
      METRICS: '/data-sources/stream/{connection_id}/metrics',
      START: '/data-sources/stream/start',
      STOP: '/data-sources/stream/stop'
    }
  },

  PIPELINES: {
    LIST: '/pipelines',
    CREATE: '/pipelines',
    GET: '/pipelines/{pipeline_id}',
    UPDATE: '/pipelines/{pipeline_id}',
    DELETE: '/pipelines/{pipeline_id}',
    START: '/pipelines/{pipeline_id}/start',
    STOP: '/pipelines/{pipeline_id}/stop',
    PAUSE: '/pipelines/{pipeline_id}/pause',
    RESUME: '/pipelines/{pipeline_id}/resume',
    RETRY: '/pipelines/{pipeline_id}/retry',
    STATUS: '/pipelines/{pipeline_id}/status',
    LOGS: '/pipelines/{pipeline_id}/logs',
    METRICS: '/pipelines/{pipeline_id}/metrics',
    VALIDATE: '/pipelines/validate',
    RUNS: '/pipelines/runs'
  },

  ANALYSIS: {
    QUALITY: {
      START: '/analysis/quality/start',
      STATUS: '/analysis/quality/{analysis_id}/status',
      REPORT: '/analysis/quality/{analysis_id}/report',
      EXPORT: '/analysis/quality/{analysis_id}/export'
    },
    INSIGHT: {
      START: '/analysis/insight/start',
      STATUS: '/analysis/insight/{analysis_id}/status',
      REPORT: '/analysis/insight/{analysis_id}/report',
      TRENDS: '/analysis/insight/{analysis_id}/trends',
      PATTERNS: '/analysis/insight/{analysis_id}/pattern/{pattern_id}',
      CORRELATIONS: '/analysis/insight/{analysis_id}/correlations',
      ANOMALIES: '/analysis/insight/{analysis_id}/anomalies',
      EXPORT: '/analysis/insight/{analysis_id}/export'
    }
  },

  MONITORING: {
    START: '/monitoring/{pipeline_id}/start',
    METRICS: '/monitoring/{pipeline_id}/metrics',
    HEALTH: '/monitoring/{pipeline_id}/health',
    PERFORMANCE: '/monitoring/{pipeline_id}/performance',
    ALERTS: {
      CONFIG: '/monitoring/{pipeline_id}/alerts/config',
      HISTORY: '/monitoring/{pipeline_id}/alerts/history'
    },
    RESOURCES: '/monitoring/{pipeline_id}/resources',
    TIME_SERIES: '/monitoring/{pipeline_id}/time-series',
    AGGREGATED: '/monitoring/{pipeline_id}/metrics/aggregated'
  },

  REPORTS: {
    LIST: '/reports',
    CREATE: '/reports',
    GET: '/reports/{report_id}',
    UPDATE: '/reports/{report_id}',
    DELETE: '/reports/{report_id}',
    STATUS: '/reports/{report_id}/status',
    EXPORT: '/reports/{report_id}/export',
    SCHEDULE: '/reports/schedule',
    METADATA: '/reports/{report_id}/metadata',
    PREVIEW: '/reports/{report_id}/preview',
    TEMPLATES: '/reports/templates'
  },

  RECOMMENDATIONS: {
    LIST: '/recommendations',
    GET: '/recommendations/{recommendation_id}',
    APPLY: '/recommendations/{recommendation_id}/apply',
    STATUS: '/recommendations/{recommendation_id}/status',
    DISMISS: '/recommendations/{recommendation_id}/dismiss',
    HISTORY: '/recommendations/pipeline/{pipeline_id}/history'
  },

  DECISIONS: {
    LIST: '/decisions',
    GET: '/decisions/{decision_id}',
    MAKE: '/decisions/{decision_id}/make',
    DEFER: '/decisions/{decision_id}/defer',
    HISTORY: '/decisions/pipeline/{pipeline_id}/history',
    IMPACT: '/decisions/{decision_id}/options/{option_id}/impact',
    LOCK: '/decisions/{decision_id}/lock',
    STATE: '/decisions/{decision_id}/state',
    UPDATE: '/decisions/{decision_id}',
    COMMENT: '/decisions/{decision_id}/comments'
  },

  SETTINGS: {
    PROFILE: '/settings/profile',
    PREFERENCES: '/settings/preferences',
    SECURITY: '/settings/security',
    NOTIFICATIONS: '/settings/notifications',
    APPEARANCE: '/settings/appearance',
    VALIDATE: '/settings/validate',
    RESET: '/settings/reset'
  },

  SYSTEM: {
    HEALTH: '/health'
  }
} as const;


// Type definitions for route helpers
export type RouteKey = keyof typeof APIRoutes;
export type SubRouteKey<T extends RouteKey> = keyof typeof APIRoutes[T];
export type NestedRouteKey<T extends RouteKey, S extends keyof typeof APIRoutes[T]> = 
    typeof APIRoutes[T][S] extends { [key: string]: string } ? keyof typeof APIRoutes[T][S] : never;

export const RouteHelper = {
    getRoute<T extends RouteKey>(
        module: T,
        route: SubRouteKey<T>,
        params?: RouteParams
    ): string {
        const baseRoute = APIRoutes[module][route];

        if (typeof baseRoute !== 'string') {
            throw new Error(`Invalid route: ${String(route)} in module ${String(module)}`);
        }

        return formatRouteWithParams(baseRoute, params);
    },

    getNestedRoute<T extends RouteKey, S extends keyof typeof APIRoutes[T], R extends NestedRouteKey<T, S>>(
        module: T,
        section: S,
        route: R,
        params?: RouteParams
    ): string {
        const sectionRoutes = APIRoutes[module][section];

        if (!isNestedRouteSection(APIRoutes[module], section)) {
            throw new Error(`Invalid section: ${String(section)} in module ${String(module)}`);
        }

        const baseRoute = (sectionRoutes as Record<string, string>)[route as string];

        if (typeof baseRoute !== 'string') {
            throw new Error(`Invalid route: ${String(route)} in section ${String(section)}`);
        }

        return formatRouteWithParams(baseRoute, params);
    }
};

// Helper functions
function normalizeRoute(route: string): string {
    return route.replace(/\/+$/, ''); // Remove trailing slashes
}

function formatRouteWithParams(route: string, params?: RouteParams): string {
    if (!params) return route;

    const validatedParams = RouteParamsSchema.parse(params);

    return Object.entries(validatedParams).reduce((formattedRoute, [key, value]) => {
        return value !== undefined 
            ? formattedRoute.replace(`{${key}}`, encodeURIComponent(String(value))) 
            : formattedRoute;
    }, route);
}

function isNestedRouteSection<T extends RouteKey>(
    routes: typeof APIRoutes[T], 
    section: keyof typeof routes
): boolean {
    return typeof routes[section] === 'object' && !Array.isArray(routes[section]);
}

// Helper type for route configuration
export interface RouteConfig<T extends RouteKey, S extends keyof typeof APIRoutes[T] = never, R extends NestedRouteKey<T, S> = never> {
    module: T;
    section?: S;
    route: S extends never ? SubRouteKey<T> : R;
    params?: RouteParams;
}

// Helper function to create route configurations
export function createRouteConfig<T extends RouteKey, S extends keyof typeof APIRoutes[T] = never, R extends NestedRouteKey<T, S> = never>(
    config: RouteConfig<T, S, R>
): RouteConfig<T, S, R> {
    return config;
}

// Helper function to get route path from configuration
export function getRoutePath<T extends RouteKey, S extends keyof typeof APIRoutes[T] = never, R extends NestedRouteKey<T, S> = never>(
    config: RouteConfig<T, S, R>
): string {
    if (config.section) {
        return RouteHelper.getNestedRoute(config.module, config.section, config.route as NestedRouteKey<T, S>, config.params);
    }
    return RouteHelper.getRoute(config.module, config.route as SubRouteKey<T>, config.params);
}
