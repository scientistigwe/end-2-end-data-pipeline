# flask_api/app/utils/route_registry.py
from enum import Enum
from typing import Dict, Any

class APIRoutes(Enum):
    # Auth Routes
    AUTH_REGISTER = '/api/v1/auth/register'
    AUTH_LOGIN = '/api/v1/auth/login'
    AUTH_REFRESH = '/api/v1/auth/refresh'
    AUTH_LOGOUT = '/api/v1/auth/logout'
    AUTH_VERIFY = '/api/v1/auth/verify'
    AUTH_FORGOT_PASSWORD = '/api/v1/auth/forgot-password'
    AUTH_RESET_PASSWORD = '/api/v1/auth/reset-password'
    AUTH_VERIFY_EMAIL = '/api/v1/auth/verify-email'
    AUTH_PROFILE = '/api/v1/auth/profile'
    AUTH_CHANGE_PASSWORD = '/api/v1/auth/change-password'

    # Pipeline Routes
    PIPELINE_LIST = '/api/v1/pipelines'
    PIPELINE_CREATE = '/api/v1/pipelines'
    PIPELINE_GET = '/api/v1/pipelines/{pipeline_id}'
    PIPELINE_UPDATE = '/api/v1/pipelines/{pipeline_id}'
    PIPELINE_DELETE = '/api/v1/pipelines/{pipeline_id}'
    PIPELINE_START = '/api/v1/pipelines/{pipeline_id}/start'
    PIPELINE_STOP = '/api/v1/pipelines/{pipeline_id}/stop'
    PIPELINE_PAUSE = '/api/v1/pipelines/{pipeline_id}/pause'
    PIPELINE_RESUME = '/api/v1/pipelines/{pipeline_id}/resume'
    PIPELINE_RETRY = '/api/v1/pipelines/{pipeline_id}/retry'
    PIPELINE_STATUS = '/api/v1/pipelines/{pipeline_id}/status'
    PIPELINE_LOGS = '/api/v1/pipelines/{pipeline_id}/logs'
    PIPELINE_METRICS = '/api/v1/pipelines/{pipeline_id}/metrics'
    PIPELINE_VALIDATE = '/api/v1/pipelines/validate'

    # Data Source Routes
    DATASOURCE_LIST = '/api/v1/sources'
    DATASOURCE_CREATE = '/api/v1/sources'
    DATASOURCE_GET = '/api/v1/sources/{source_id}'
    DATASOURCE_UPDATE = '/api/v1/sources/{source_id}'
    DATASOURCE_DELETE = '/api/v1/sources/{source_id}'
    DATASOURCE_TEST = '/api/v1/sources/{source_id}/test'
    DATASOURCE_SYNC = '/api/v1/sources/{source_id}/sync'
    DATASOURCE_VALIDATE = '/api/v1/sources/{source_id}/validate'
    DATASOURCE_PREVIEW = '/api/v1/sources/{source_id}/preview'
    
    # File Source Routes
    DATASOURCE_FILE_UPLOAD = '/api/v1/sources/file/upload'
    DATASOURCE_FILE_PARSE = '/api/v1/sources/file/{file_id}/parse'
    DATASOURCE_FILE_METADATA = '/api/v1/sources/file/{file_id}/metadata'

    # Database Source Routes
    DATASOURCE_DB_CONNECT = '/api/v1/sources/database/connect'
    DATASOURCE_DB_TEST = '/api/v1/sources/database/{connection_id}/test'
    DATASOURCE_DB_QUERY = '/api/v1/sources/database/{connection_id}/query'
    DATASOURCE_DB_SCHEMA = '/api/v1/sources/database/{connection_id}/schema'
    DATASOURCE_DB_METADATA = '/api/v1/sources/database/metadata'

    # API Source Routes
    DATASOURCE_API_CONNECT = '/api/v1/sources/api/connect'
    DATASOURCE_API_TEST = '/api/v1/sources/api/test-endpoint'
    DATASOURCE_API_EXECUTE = '/api/v1/sources/api/{connection_id}/execute'
    DATASOURCE_API_STATUS = '/api/v1/sources/api/{connection_id}/status'
    DATASOURCE_API_METADATA = '/api/v1/sources/api/metadata'

    # S3 Source Routes
    DATASOURCE_S3_CONNECT = '/api/v1/sources/s3/connect'
    DATASOURCE_S3_LIST = '/api/v1/sources/s3/{connection_id}/list'
    DATASOURCE_S3_INFO = '/api/v1/sources/s3/{connection_id}/info'
    DATASOURCE_S3_DOWNLOAD = '/api/v1/sources/s3/{connection_id}/download'
    DATASOURCE_S3_METADATA = '/api/v1/sources/s3/metadata'

    # Stream Source Routes
    DATASOURCE_STREAM_CONNECT = '/api/v1/sources/stream/connect'
    DATASOURCE_STREAM_STATUS = '/api/v1/sources/stream/{connection_id}/status'
    DATASOURCE_STREAM_METRICS = '/api/v1/sources/stream/{connection_id}/metrics'
    DATASOURCE_STREAM_START = '/api/v1/sources/stream/start'
    DATASOURCE_STREAM_STOP = '/api/v1/sources/stream/stop'

    # Analysis Routes
    ANALYSIS_QUALITY_START = '/api/v1/analysis/quality/start'
    ANALYSIS_QUALITY_STATUS = '/api/v1/analysis/quality/{analysis_id}/status'
    ANALYSIS_QUALITY_REPORT = '/api/v1/analysis/quality/{analysis_id}/report'
    ANALYSIS_QUALITY_EXPORT = '/api/v1/analysis/quality/{analysis_id}/export'

    ANALYSIS_INSIGHT_START = '/api/v1/analysis/insight/start'
    ANALYSIS_INSIGHT_STATUS = '/api/v1/analysis/insight/{analysis_id}/status'
    ANALYSIS_INSIGHT_REPORT = '/api/v1/analysis/insight/{analysis_id}/report'
    ANALYSIS_INSIGHT_TRENDS = '/api/v1/analysis/insight/{analysis_id}/trends'
    ANALYSIS_INSIGHT_PATTERNS = '/api/v1/analysis/insight/{analysis_id}/pattern/{pattern_id}'
    ANALYSIS_INSIGHT_CORRELATIONS = '/api/v1/analysis/insight/{analysis_id}/correlations'
    ANALYSIS_INSIGHT_ANOMALIES = '/api/v1/analysis/insight/{analysis_id}/anomalies'
    ANALYSIS_INSIGHT_EXPORT = '/api/v1/analysis/insight/{analysis_id}/export'

    # Monitoring Routes
    MONITORING_START = '/api/v1/monitoring/{pipeline_id}/start'
    MONITORING_METRICS = '/api/v1/monitoring/{pipeline_id}/metrics'
    MONITORING_HEALTH = '/api/v1/monitoring/{pipeline_id}/health'
    MONITORING_PERFORMANCE = '/api/v1/monitoring/{pipeline_id}/performance'
    MONITORING_ALERTS_CONFIG = '/api/v1/monitoring/{pipeline_id}/alerts/config'
    MONITORING_ALERTS_HISTORY = '/api/v1/monitoring/{pipeline_id}/alerts/history'
    MONITORING_RESOURCES = '/api/v1/monitoring/{pipeline_id}/resources'
    MONITORING_TIME_SERIES = '/api/v1/monitoring/{pipeline_id}/time-series'
    MONITORING_AGGREGATED = '/api/v1/monitoring/{pipeline_id}/metrics/aggregated'

    # Reports Routes
    REPORTS_LIST = '/api/v1/reports'
    REPORTS_CREATE = '/api/v1/reports'
    REPORTS_GET = '/api/v1/reports/{report_id}'
    REPORTS_UPDATE = '/api/v1/reports/{report_id}'
    REPORTS_DELETE = '/api/v1/reports/{report_id}'
    REPORTS_STATUS = '/api/v1/reports/{report_id}/status'
    REPORTS_EXPORT = '/api/v1/reports/{report_id}/export'
    REPORTS_SCHEDULE = '/api/v1/reports/schedule'
    REPORTS_METADATA = '/api/v1/reports/{report_id}/metadata'
    REPORTS_PREVIEW = '/api/v1/reports/{report_id}/preview'
    REPORTS_TEMPLATES = '/api/v1/reports/templates'

    # Recommendations Routes
    RECOMMENDATIONS_LIST = '/api/v1/recommendations'
    RECOMMENDATIONS_GET = '/api/v1/recommendations/{recommendation_id}'
    RECOMMENDATIONS_APPLY = '/api/v1/recommendations/{recommendation_id}/apply'
    RECOMMENDATIONS_STATUS = '/api/v1/recommendations/{recommendation_id}/status'
    RECOMMENDATIONS_DISMISS = '/api/v1/recommendations/{recommendation_id}/dismiss'
    RECOMMENDATIONS_HISTORY = '/api/v1/recommendations/pipeline/{pipeline_id}/history'

    # Decisions Routes
    DECISIONS_LIST = '/api/v1/decisions'
    DECISIONS_GET = '/api/v1/decisions/{decision_id}'
    DECISIONS_MAKE = '/api/v1/decisions/{decision_id}/make'
    DECISIONS_DEFER = '/api/v1/decisions/{decision_id}/defer'
    DECISIONS_HISTORY = '/api/v1/decisions/pipeline/{pipeline_id}/history'
    DECISIONS_IMPACT = '/api/v1/decisions/{decision_id}/options/{option_id}/impact'

    # Settings Routes
    SETTINGS_PROFILE = '/api/v1/settings/profile'
    SETTINGS_PREFERENCES = '/api/v1/settings/preferences'
    SETTINGS_SECURITY = '/api/v1/settings/security'
    SETTINGS_NOTIFICATIONS = '/api/v1/settings/notifications'
    SETTINGS_APPEARANCE = '/api/v1/settings/appearance'
    SETTINGS_VALIDATE = '/api/v1/settings/validate'
    SETTINGS_RESET = '/api/v1/settings/reset'

    @classmethod
    def get_route(cls, route_name: str, **kwargs: Dict[str, Any]) -> str:
        """Get formatted route with parameters

        Args:
            route_name: Name of the route from APIRoutes
            **kwargs: Route parameters to be formatted

        Returns:
            Formatted route string with parameters
        
        Example:
            >>> APIRoutes.get_route('PIPELINE_STATUS', pipeline_id='123')
            '/api/v1/pipeline/123/status'
        """
        route = cls[route_name].value
        return route.format(**kwargs) if kwargs else route