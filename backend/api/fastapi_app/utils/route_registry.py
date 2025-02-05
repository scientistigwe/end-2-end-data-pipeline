from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, TypedDict

@dataclass
class RouteDefinition:
    """Route definition with metadata"""
    path: str
    methods: List[str]
    requires_auth: bool = True
    rate_limit: Optional[int] = None
    cache_ttl: Optional[int] = None

class RouteParams(TypedDict, total=False):
    source_id: str
    pipeline_id: str
    analysis_id: str
    file_id: str
    connection_id: str
    decision_id: str
    option_id: str
    pattern_id: str
    report_id: str
    recommendation_id: str

class APIRoutes(Enum):
    """API route registry with explicit auth requirements"""

    # Auth Routes
    AUTH_REGISTER = RouteDefinition('/auth/register', ['POST'], requires_auth=False)
    AUTH_LOGIN = RouteDefinition('/auth/login', ['POST'], requires_auth=False)
    AUTH_LOGOUT = RouteDefinition('/auth/logout', ['POST'], requires_auth=True)
    AUTH_VERIFY = RouteDefinition('/auth/verify', ['POST'], requires_auth=False)
    AUTH_REFRESH = RouteDefinition('/auth/refresh', ['POST'], requires_auth=False)
    AUTH_FORGOT_PASSWORD = RouteDefinition('/auth/forgot-password', ['POST'], requires_auth=False)
    AUTH_RESET_PASSWORD = RouteDefinition('/auth/reset-password', ['POST'], requires_auth=False)
    AUTH_VERIFY_EMAIL = RouteDefinition('/auth/verify-email', ['POST'], requires_auth=False)
    AUTH_PROFILE = RouteDefinition('/auth/profile', ['GET', 'PUT'], requires_auth=True)
    AUTH_CHANGE_PASSWORD = RouteDefinition('/auth/change-password', ['POST'], requires_auth=True)

    # Data Source Routes - Common
    DATASOURCE_LIST = RouteDefinition('/data-sources', ['GET'])
    DATASOURCE_CREATE = RouteDefinition('/data-sources', ['POST'])
    DATASOURCE_GET = RouteDefinition('/data-sources/{source_id}', ['GET'])
    DATASOURCE_UPDATE = RouteDefinition('/data-sources/{source_id}', ['PUT'])
    DATASOURCE_DELETE = RouteDefinition('/data-sources/{source_id}', ['DELETE'])
    DATASOURCE_TEST = RouteDefinition('/data-sources/{source_id}/test', ['POST'])
    DATASOURCE_SYNC = RouteDefinition('/data-sources/{source_id}/sync', ['POST'])
    DATASOURCE_VALIDATE = RouteDefinition('/data-sources/{source_id}/validate', ['POST'])
    DATASOURCE_PREVIEW = RouteDefinition('/data-sources/{source_id}/preview', ['GET'])
    DATASOURCE_CONNECTION_STATUS = RouteDefinition('/data-sources/connection/{connection_id}/status', ['GET'])
    DATASOURCE_CONNECTION_DISCONNECT = RouteDefinition('/data-sources/connection/{connection_id}/disconnect', ['POST'])

    # File Source Routes
    DATASOURCE_FILE_UPLOAD = RouteDefinition('/data-sources/file/upload', ['POST'])
    DATASOURCE_FILE_PARSE = RouteDefinition('/data-sources/file/{file_id}/parse', ['POST'])
    DATASOURCE_FILE_METADATA = RouteDefinition('/data-sources/file/{file_id}/metadata', ['GET'])

    # Database Source Routes
    DATASOURCE_DB_CONNECT = RouteDefinition('/data-sources/db/connect', ['POST'])
    DATASOURCE_DB_TEST = RouteDefinition('/data-sources/db/{connection_id}/test', ['POST'])
    DATASOURCE_DB_QUERY = RouteDefinition('/data-sources/db/{connection_id}/query', ['POST'])
    DATASOURCE_DB_SCHEMA = RouteDefinition('/data-sources/db/{connection_id}/schema', ['GET'])
    DATASOURCE_DB_METADATA = RouteDefinition('/data-sources/db/metadata', ['GET'])

    # API Source Routes
    DATASOURCE_API_CONNECT = RouteDefinition('/data-sources/api/connect', ['POST'])
    DATASOURCE_API_TEST = RouteDefinition('/data-sources/api/test-endpoint', ['POST'])
    DATASOURCE_API_EXECUTE = RouteDefinition('/data-sources/api/{connection_id}/execute', ['POST'])
    DATASOURCE_API_STATUS = RouteDefinition('/data-sources/api/{connection_id}/status', ['GET'])
    DATASOURCE_API_METADATA = RouteDefinition('/data-sources/api/metadata', ['GET'])

    # S3 Source Routes
    DATASOURCE_S3_CONNECT = RouteDefinition('/data-sources/s3/connect', ['POST'])
    DATASOURCE_S3_LIST = RouteDefinition('/data-sources/s3/{connection_id}/list', ['GET'])
    DATASOURCE_S3_INFO = RouteDefinition('/data-sources/s3/{connection_id}/info', ['GET'])
    DATASOURCE_S3_DOWNLOAD = RouteDefinition('/data-sources/s3/{connection_id}/download', ['GET'])
    DATASOURCE_S3_METADATA = RouteDefinition('/data-sources/s3/metadata', ['GET'])

    # Stream Source Routes
    DATASOURCE_STREAM_CONNECT = RouteDefinition('/data-sources/stream/connect', ['POST'])
    DATASOURCE_STREAM_STATUS = RouteDefinition('/data-sources/stream/{connection_id}/status', ['GET'])
    DATASOURCE_STREAM_METRICS = RouteDefinition('/data-sources/stream/{connection_id}/metrics', ['GET'])
    DATASOURCE_STREAM_START = RouteDefinition('/data-sources/stream/start', ['POST'])
    DATASOURCE_STREAM_STOP = RouteDefinition('/data-sources/stream/stop', ['POST'])

    # Pipeline Routes
    PIPELINE_LIST = RouteDefinition('/pipelines', ['GET'])
    PIPELINE_CREATE = RouteDefinition('/pipelines', ['POST'])
    PIPELINE_GET = RouteDefinition('/pipelines/{pipeline_id}', ['GET'])
    PIPELINE_UPDATE = RouteDefinition('/pipelines/{pipeline_id}', ['PUT'])
    PIPELINE_DELETE = RouteDefinition('/pipelines/{pipeline_id}', ['DELETE'])
    PIPELINE_START = RouteDefinition('/pipelines/{pipeline_id}/start', ['POST'])
    PIPELINE_STOP = RouteDefinition('/pipelines/{pipeline_id}/stop', ['POST'])
    PIPELINE_PAUSE = RouteDefinition('/pipelines/{pipeline_id}/pause', ['POST'])
    PIPELINE_RESUME = RouteDefinition('/pipelines/{pipeline_id}/resume', ['POST'])
    PIPELINE_RETRY = RouteDefinition('/pipelines/{pipeline_id}/retry', ['POST'])
    PIPELINE_STATUS = RouteDefinition('/pipelines/{pipeline_id}/status', ['GET'])
    PIPELINE_LOGS = RouteDefinition('/pipelines/{pipeline_id}/logs', ['GET'])
    PIPELINE_METRICS = RouteDefinition('/pipelines/{pipeline_id}/metrics', ['GET'])
    PIPELINE_VALIDATE = RouteDefinition('/pipelines/validate', ['POST'])
    PIPELINE_RUNS = RouteDefinition('/pipelines/runs', ['GET'])

    # Analytics Routes
    ANALYTICS_QUALITY_START = RouteDefinition('/insight/quality/start', ['POST'])
    ANALYTICS_QUALITY_STATUS = RouteDefinition('/insight/quality/{analysis_id}/status', ['GET'])
    ANALYTICS_QUALITY_REPORT = RouteDefinition('/insight/quality/{analysis_id}/report', ['GET'])
    ANALYTICS_QUALITY_EXPORT = RouteDefinition('/insight/quality/{analysis_id}/export', ['GET'])

    ANALYTICS_INSIGHT_START = RouteDefinition('/insight/insight/start', ['POST'])
    ANALYTICS_INSIGHT_STATUS = RouteDefinition('/insight/insight/{analysis_id}/status', ['GET'])
    ANALYTICS_INSIGHT_REPORT = RouteDefinition('/insight/insight/{analysis_id}/report', ['GET'])
    ANALYTICS_INSIGHT_TRENDS = RouteDefinition('/insight/insight/{analysis_id}/trends', ['GET'])
    ANALYTICS_INSIGHT_PATTERNS = RouteDefinition('/insight/insight/{analysis_id}/pattern/{pattern_id}', ['GET'])
    ANALYTICS_INSIGHT_CORRELATIONS = RouteDefinition('/insight/insight/{analysis_id}/correlations', ['GET'])
    ANALYTICS_INSIGHT_ANOMALIES = RouteDefinition('/insight/insight/{analysis_id}/anomalies', ['GET'])
    ANALYTICS_INSIGHT_EXPORT = RouteDefinition('/insight/insight/{analysis_id}/export', ['GET'])

    # Monitoring Routes
    MONITORING_START = RouteDefinition('/monitoring/{pipeline_id}/start', ['POST'])
    MONITORING_METRICS = RouteDefinition('/monitoring/{pipeline_id}/metrics', ['GET'])
    MONITORING_HEALTH = RouteDefinition('/monitoring/{pipeline_id}/health', ['GET'])
    MONITORING_PERFORMANCE = RouteDefinition('/monitoring/{pipeline_id}/performance', ['GET'])
    MONITORING_ALERTS_CONFIG = RouteDefinition('/monitoring/{pipeline_id}/alerts/config', ['GET', 'PUT'])
    MONITORING_ALERTS_HISTORY = RouteDefinition('/monitoring/{pipeline_id}/alerts/history', ['GET'])
    MONITORING_RESOURCES = RouteDefinition('/monitoring/{pipeline_id}/resources', ['GET'])
    MONITORING_TIME_SERIES = RouteDefinition('/monitoring/{pipeline_id}/time-series', ['GET'])
    MONITORING_AGGREGATED = RouteDefinition('/monitoring/{pipeline_id}/metrics/aggregated', ['GET'])

    # Reports Routes
    REPORTS_LIST = RouteDefinition('/reports', ['GET'])
    REPORTS_CREATE = RouteDefinition('/reports', ['POST'])
    REPORTS_GET = RouteDefinition('/reports/{report_id}', ['GET'])
    REPORTS_UPDATE = RouteDefinition('/reports/{report_id}', ['PUT'])
    REPORTS_DELETE = RouteDefinition('/reports/{report_id}', ['DELETE'])
    REPORTS_STATUS = RouteDefinition('/reports/{report_id}/status', ['GET'])
    REPORTS_EXPORT = RouteDefinition('/reports/{report_id}/export', ['GET'])
    REPORTS_SCHEDULE = RouteDefinition('/reports/schedule', ['POST'])
    REPORTS_METADATA = RouteDefinition('/reports/{report_id}/metadata', ['GET'])
    REPORTS_PREVIEW = RouteDefinition('/reports/{report_id}/preview', ['GET'])
    REPORTS_TEMPLATES = RouteDefinition('/reports/templates', ['GET'])

    # Recommendations Routes
    RECOMMENDATIONS_LIST = RouteDefinition('/recommendations', ['GET'])
    RECOMMENDATIONS_GET = RouteDefinition('/recommendations/{recommendation_id}', ['GET'])
    RECOMMENDATIONS_APPLY = RouteDefinition('/recommendations/{recommendation_id}/apply', ['POST'])
    RECOMMENDATIONS_STATUS = RouteDefinition('/recommendations/{recommendation_id}/status', ['GET'])
    RECOMMENDATIONS_DISMISS = RouteDefinition('/recommendations/{recommendation_id}/dismiss', ['POST'])
    RECOMMENDATIONS_HISTORY = RouteDefinition('/recommendations/pipeline/{pipeline_id}/history', ['GET'])

    # Decisions Routes
    DECISIONS_LIST = RouteDefinition('/decisions', ['GET'])
    DECISIONS_GET = RouteDefinition('/decisions/{decision_id}', ['GET'])
    DECISIONS_MAKE = RouteDefinition('/decisions/{decision_id}/make', ['POST'])
    DECISIONS_DEFER = RouteDefinition('/decisions/{decision_id}/defer', ['POST'])
    DECISIONS_HISTORY = RouteDefinition('/decisions/pipeline/{pipeline_id}/history', ['GET'])
    DECISIONS_IMPACT = RouteDefinition('/decisions/{decision_id}/options/{option_id}/impact', ['GET'])
    DECISIONS_LOCK = RouteDefinition('/decisions/{decision_id}/lock', ['POST'])
    DECISIONS_STATE = RouteDefinition('/decisions/{decision_id}/state', ['GET'])
    DECISIONS_UPDATE = RouteDefinition('/decisions/{decision_id}', ['PUT'])
    DECISIONS_COMMENT = RouteDefinition('/decisions/{decision_id}/comments', ['POST'])

    # Settings Routes
    SETTINGS_PROFILE = RouteDefinition('/settings/profile', ['GET', 'PUT'])
    SETTINGS_PREFERENCES = RouteDefinition('/settings/preferences', ['GET', 'PUT'])
    SETTINGS_SECURITY = RouteDefinition('/settings/security', ['GET', 'PUT'])
    SETTINGS_NOTIFICATIONS = RouteDefinition('/settings/notifications', ['GET', 'PUT'])
    SETTINGS_APPEARANCE = RouteDefinition('/settings/appearance', ['GET', 'PUT'])
    SETTINGS_VALIDATE = RouteDefinition('/settings/validate', ['POST'])
    SETTINGS_RESET = RouteDefinition('/settings/reset', ['POST'])

    # System Routes
    HEALTH_CHECK = RouteDefinition('/health', ['GET'], requires_auth=False, cache_ttl=60)

    @classmethod
    def get_route(cls, route_name: str, **params) -> str:
        """Get formatted route path with parameters"""
        route = cls[route_name].value.path
        return route.format(**params) if params else route

    @classmethod
    def get_methods(cls, route_name: str) -> List[str]:
        """Get allowed methods for route"""
        return cls[route_name].value.methods

    @classmethod
    def get_definition(cls, route_name: str) -> RouteDefinition:
        """Get complete route definition"""
        return cls[route_name].value

def normalize_route(route: str) -> str:
    """Normalize route format by removing trailing slashes"""
    return route.rstrip('/')