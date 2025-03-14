/**
 * Enum for HTTP Methods
 */
export enum HttpMethod {
    GET = 'GET',
    POST = 'POST',
    PUT = 'PUT',
    DELETE = 'DELETE'
}

/**
 * Enum for Data Source Types
 */
export enum DataSourceType {
    FILE = 'file',
    DATABASE = 'database',
    API = 'api',
    S3 = 's3',
    STREAM = 'stream'
}

/**
 * Interface for route parameters with enhanced type safety
 */
export interface RouteParams {
    source_id?: string;
    pipeline_id?: string;
    analysis_id?: string;
    generation_id?: string;
    output_id?: string;
    template_id?: string;
    recommendation_id?: string;
    decision_id?: string;
    file_id?: string;
    connection_id?: string;
    alert_id?: string;
}

/**
 * Type-safe API route configuration
 */
export const APIRoutes = {
    AUTH: {
        LOGIN: '/auth/login',                    // POST: Login user
        REGISTER: '/auth/register',              // POST: Register new user
        LOGOUT: '/auth/logout',                  // POST: Logout user
        REFRESH: '/auth/refresh',                // POST: Refresh token
        PROFILE: {
            GET: '/auth/profile',                // GET: Get user profile
            UPDATE: '/auth/profile'              // PUT: Update user profile
        },
        PASSWORD: {
            FORGOT: '/auth/password/forgot',     // POST: Initiate password reset
            RESET: '/auth/password/reset',       // POST: Reset password
            CHANGE: '/auth/password/change'      // POST: Change password
        },
        EMAIL: {
            VERIFY: '/auth/email/verify',        // POST: Verify email
            RESEND: '/auth/email/verify/resend'  // POST: Resend verification
        },
        MFA: {
            SETUP: '/auth/mfa/setup',            // POST: Setup MFA
            VERIFY: '/auth/mfa/verify'           // POST: Verify MFA code
        },
        SESSION: {
            VALIDATE: '/auth/session/validate',  // POST: Validate session
        },
        PERMISSIONS: '/auth/permissions'         // GET: Get user permissions
    },

    PIPELINE: {
        LIST: '/pipelines',                       // GET: List pipelines
        CREATE: '/pipelines',                     // POST: Create pipeline
        GET: '/pipelines/{pipeline_id}',          // GET: Get pipeline details
        START: '/pipelines/{pipeline_id}/start',  // POST: Start pipeline
        STATUS: '/pipelines/{pipeline_id}/status', // GET: Get pipeline status
        LOGS: '/pipelines/{pipeline_id}/logs',    // GET: Get pipeline logs
        METRICS: '/pipelines/{pipeline_id}/metrics' // GET: Get pipeline metrics
    },

    QUALITY: {
        ANALYZE: '/quality/analyze',             // POST: Start quality analysis
        STATUS: '/quality/{analysis_id}/status', // GET: Get analysis status
        RESULTS: '/quality/{analysis_id}/results', // GET: Get analysis results
        ISSUES: '/quality/{analysis_id}/issues', // GET: Get quality issues
        REMEDIATION: '/quality/{analysis_id}/remediation', // GET: Get remediation plan
        RULES: '/quality/config/rules'           // POST: Update validation rules
    },

    DATA_SOURCES: {
        LIST: '/data-sources',                   // GET: List sources
        CREATE: '/data-sources',                 // POST: Create source
        GET: '/data-sources/{source_id}',        // GET: Get source details
        UPDATE: '/data-sources/{source_id}',     // PUT: Update source
        DELETE: '/data-sources/{source_id}',     // DELETE: Delete source
        TEST: '/data-sources/{source_id}/test',
        SYNC: '/data-sources/{source_id}/sync',
        VALIDATE: '/data-sources/{source_id}/validate',
        PREVIEW: '/data-sources/{source_id}/preview', // GET: Preview source data
        CONNECTION: {
            STATUS: '/data-sources/connection/{connection_id}/status',
            DISCONNECT: '/data-sources/connection/{connection_id}/disconnect'
        },
        FILE: {
            UPLOAD: '/data-sources/file/upload',
            PARSE: '/data-sources/file/{file_id}/parse',
            METADATA: '/data-sources/file/{file_id}/metadata'
        },
        DB: {
            CONNECT: '/data-sources/db/connect',
            TEST: '/data-sources/db/{connection_id}/test',
            QUERY: '/data-sources/db/{connection_id}/query',
            SCHEMA: '/data-sources/db/{connection_id}/schema',
            METADATA: '/data-sources/db/metadata'
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

    STAGING: {
        OUTPUTS: {
            LIST: '/staging/outputs',
            GET: '/staging/outputs/{output_id}',
            HISTORY: '/staging/outputs/{output_id}/history',
            ARCHIVE: '/staging/outputs/{output_id}/archive'
        },
        METRICS: '/staging/metrics',
        PIPELINE_STATUS: '/staging/pipelines/{pipeline_id}/status',
        CLEANUP: '/staging/cleanup'
    },

    MONITORING: {
        METRICS: '/monitoring/{pipeline_id}/metrics',
        HEALTH: '/monitoring/{pipeline_id}/health',
        PERFORMANCE: '/monitoring/{pipeline_id}/performance',
        ALERTS: {
            CONFIG: '/monitoring/{pipeline_id}/alerts/config',
            HISTORY: '/monitoring/{pipeline_id}/alerts/history'
        },
        RESOURCES: '/monitoring/{pipeline_id}/resources',
        METRICS_AGGREGATED: '/monitoring/{pipeline_id}/metrics/aggregated'
    },
    DECISIONS: {
        LIST: '/decisions',
        PIPELINE: '/decisions/{pipeline_id}/pending',
        MAKE: '/decisions/{decision_id}/make',
        FEEDBACK: '/decisions/{decision_id}/feedback',
        HISTORY: '/decisions/{pipeline_id}/history',
        IMPACT: '/decisions/{decision_id}/impact'
    },
    RECOMMENDATIONS: {
        LIST: '/recommendations',
        PIPELINE: '/recommendations/{pipeline_id}',
        APPLY: '/recommendations/{recommendation_id}/apply',
        DISMISS: '/recommendations/{recommendation_id}/dismiss',
        STATUS: '/recommendations/{recommendation_id}/status'
    },

    REPORTS: {
        LIST: '/reports',
        CREATE: '/reports',
        GET: '/reports/{report_id}',
        UPDATE: '/reports/{report_id}',
        GENERATE: '/reports/{report_id}/generate',
        EXPORT: '/reports/{report_id}/export',
        SCHEDULE: '/reports/schedule',
        TEMPLATES: '/reports/templates'
    },

    INSIGHTS: {
        GENERATE: '/insights/generate',          // POST: Generate insights
        STATUS: '/insights/{generation_id}/status', // GET: Get generation status
        RESULTS: '/insights/{generation_id}/results', // GET: Get generated insights
        TRENDS: '/insights/{generation_id}/trends', // GET: Get trend insights
        ANOMALIES: '/insights/{generation_id}/anomalies', // GET: Get anomaly insights
        CORRELATIONS: '/insights/{generation_id}/correlations', // GET: Get correlation insights
        VALIDATE: '/insights/{generation_id}/validate' // POST: Validate insights
    },
    SETTINGS: {
        PROFILE: '/settings/profile',
        NOTIFICATIONS: '/settings/notifications',
        SECURITY: '/settings/security',
        APPEARANCE: '/settings/appearance',
        SYSTEM: '/settings/system',
        VALIDATE: '/settings/validate',
        RESET: '/settings/reset',
        SYNC: '/settings/sync'
    }
} as const;

/**
 * Type definitions for route helpers
 */
export type RouteKey = keyof typeof APIRoutes;
export type SubRouteKey<T extends RouteKey> = keyof (typeof APIRoutes)[T];
export type AuthRouteKey = keyof (typeof APIRoutes)['AUTH'];
export type NestedRouteKey<T extends RouteKey, S extends SubRouteKey<T>> = 
    typeof APIRoutes[T][S] extends { [key: string]: string } ? keyof typeof APIRoutes[T][S] : never;

/**
 * Route Helper Class with utility methods
 */
export class RouteHelper {
    /**
     * Removes trailing slashes from a route
     */
    private static normalizeRoute(route: string): string {
        return route.replace(/\/+$/, '');
    }

    /**
     * Formats a route with provided parameters
     */
    private static formatRouteWithParams(route: string, params?: RouteParams): string {
        if (!params) return route;

        let formattedRoute = route;
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined) {
                formattedRoute = formattedRoute.replace(
                    new RegExp(`{${key}}`, 'g'),
                    encodeURIComponent(String(value))
                );
            }
        });

        return this.normalizeRoute(formattedRoute);
    }

    /**
     * Gets a route with improved error handling
     */
    static getRoute<T extends RouteKey>(
        module: T,
        route: SubRouteKey<T>,
        params?: RouteParams
    ): string {
        const moduleRoutes = APIRoutes[module];
        const baseRoute = moduleRoutes[route];

        if (!baseRoute || typeof baseRoute !== 'string') {
            throw new Error(
                `Invalid route: ${String(route)} in module ${String(module)}`
            );
        }

        return this.formatRouteWithParams(baseRoute, params);
    }

    /**
     * Gets a nested route with improved type checking
     */
    static getNestedRoute<
        T extends RouteKey,
        S extends SubRouteKey<T>,
        R extends NestedRouteKey<T, S>
    >(
        module: T,
        section: S,
        route: R,
        params?: RouteParams
    ): string {
        const sectionRoutes = APIRoutes[module][section];

        if (!sectionRoutes || typeof sectionRoutes !== 'object') {
            throw new Error(
                `Invalid section: ${String(section)} in module ${String(module)}`
            );
        }

        const baseRoute = sectionRoutes[route];

        if (!baseRoute || typeof baseRoute !== 'string') {
            throw new Error(
                `Invalid route: ${String(route)} in section ${String(section)}`
            );
        }

        return this.formatRouteWithParams(baseRoute, params);
    }
}