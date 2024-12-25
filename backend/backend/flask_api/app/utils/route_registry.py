# flask_api/app/utils/route_registry.py
from enum import Enum
from typing import Dict, Any

class APIRoutes(Enum):
    # Auth Routes
    AUTH_REGISTER = 'auth/register'
    AUTH_LOGIN = '/auth/login'
    AUTH_REFRESH = '/auth/refresh'
    AUTH_LOGOUT = '/auth/logout'
    AUTH_VERIFY = '/auth/verify'
    AUTH_FORGOT_PASSWORD = '/auth/forgot-password'
    AUTH_RESET_PASSWORD = '/auth/reset-password'
    AUTH_VERIFY_EMAIL = '/auth/verify-email'
    AUTH_PROFILE = '/auth/profile'
    AUTH_CHANGE_PASSWORD = '/auth/change-password'

    # Pipeline Routes
    PIPELINE_LIST = '/pipelines'
    PIPELINE_CREATE = '/pipelines'
    PIPELINE_GET = '/pipelines/{pipeline_id}'
    PIPELINE_UPDATE = '/pipelines/{pipeline_id}'
    PIPELINE_DELETE = '/pipelines/{pipeline_id}'
    PIPELINE_START = '/pipelines/{pipeline_id}/start'
    PIPELINE_STOP = '/pipelines/{pipeline_id}/stop'
    PIPELINE_PAUSE = '/pipelines/{pipeline_id}/pause'
    PIPELINE_RESUME = '/pipelines/{pipeline_id}/resume'
    PIPELINE_RETRY = '/pipelines/{pipeline_id}/retry'
    PIPELINE_STATUS = '/pipelines/{pipeline_id}/status'
    PIPELINE_LOGS = '/pipelines/{pipeline_id}/logs'
    PIPELINE_METRICS = '/pipelines/{pipeline_id}/metrics'
    PIPELINE_VALIDATE = '/pipelines/validate'

    # Data Source Routes
    DATASOURCE_LIST = '/sources'
    DATASOURCE_CREATE = '/sources'
    DATASOURCE_GET = '/sources/{source_id}'
    DATASOURCE_UPDATE = '/sources/{source_id}'
    DATASOURCE_DELETE = '/sources/{source_id}'
    DATASOURCE_TEST = '/sources/{source_id}/test'
    DATASOURCE_SYNC = '/sources/{source_id}/sync'
    DATASOURCE_VALIDATE = '/sources/{source_id}/validate'
    DATASOURCE_PREVIEW = '/sources/{source_id}/preview'
    
    # File Source Routes
    DATASOURCE_FILE_UPLOAD = '/sources/file/upload'
    DATASOURCE_FILE_PARSE = '/sources/file/{file_id}/parse'
    DATASOURCE_FILE_METADATA = '/sources/file/{file_id}/metadata'

    # Database Source Routes
    DATASOURCE_DB_CONNECT = '/sources/database/connect'
    DATASOURCE_DB_TEST = '/sources/database/{connection_id}/test'
    DATASOURCE_DB_QUERY = '/sources/database/{connection_id}/query'
    DATASOURCE_DB_SCHEMA = '/sources/database/{connection_id}/schema'
    DATASOURCE_DB_METADATA = '/sources/database/metadata'

    # API Source Routes
    DATASOURCE_API_CONNECT = '/sources/api/connect'
    DATASOURCE_API_TEST = '/sources/api/test-endpoint'
    DATASOURCE_API_EXECUTE = '/sources/api/{connection_id}/execute'
    DATASOURCE_API_STATUS = '/sources/api/{connection_id}/status'
    DATASOURCE_API_METADATA = '/sources/api/metadata'

    # S3 Source Routes
    DATASOURCE_S3_CONNECT = '/sources/s3/connect'
    DATASOURCE_S3_LIST = '/sources/s3/{connection_id}/list'
    DATASOURCE_S3_INFO = '/sources/s3/{connection_id}/info'
    DATASOURCE_S3_DOWNLOAD = '/sources/s3/{connection_id}/download'
    DATASOURCE_S3_METADATA = '/sources/s3/metadata'

    # Stream Source Routes
    DATASOURCE_STREAM_CONNECT = '/sources/stream/connect'
    DATASOURCE_STREAM_STATUS = '/sources/stream/{connection_id}/status'
    DATASOURCE_STREAM_METRICS = '/sources/stream/{connection_id}/metrics'
    DATASOURCE_STREAM_START = '/sources/stream/start'
    DATASOURCE_STREAM_STOP = '/sources/stream/stop'

    # Analysis Routes
    ANALYSIS_QUALITY_START = '/analysis/quality/start'
    ANALYSIS_QUALITY_STATUS = '/analysis/quality/{analysis_id}/status'
    ANALYSIS_QUALITY_REPORT = '/analysis/quality/{analysis_id}/report'
    ANALYSIS_QUALITY_EXPORT = '/analysis/quality/{analysis_id}/export'

    ANALYSIS_INSIGHT_START = '/analysis/insight/start'
    ANALYSIS_INSIGHT_STATUS = '/analysis/insight/{analysis_id}/status'
    ANALYSIS_INSIGHT_REPORT = '/analysis/insight/{analysis_id}/report'
    ANALYSIS_INSIGHT_TRENDS = '/analysis/insight/{analysis_id}/trends'
    ANALYSIS_INSIGHT_PATTERNS = '/analysis/insight/{analysis_id}/pattern/{pattern_id}'
    ANALYSIS_INSIGHT_CORRELATIONS = '/analysis/insight/{analysis_id}/correlations'
    ANALYSIS_INSIGHT_ANOMALIES = '/analysis/insight/{analysis_id}/anomalies'
    ANALYSIS_INSIGHT_EXPORT = '/analysis/insight/{analysis_id}/export'

    # Monitoring Routes
    MONITORING_START = '/monitoring/{pipeline_id}/start'
    MONITORING_METRICS = '/monitoring/{pipeline_id}/metrics'
    MONITORING_HEALTH = '/monitoring/{pipeline_id}/health'
    MONITORING_PERFORMANCE = '/monitoring/{pipeline_id}/performance'
    MONITORING_ALERTS_CONFIG = '/monitoring/{pipeline_id}/alerts/config'
    MONITORING_ALERTS_HISTORY = '/monitoring/{pipeline_id}/alerts/history'
    MONITORING_RESOURCES = '/monitoring/{pipeline_id}/resources'
    MONITORING_TIME_SERIES = '/monitoring/{pipeline_id}/time-series'
    MONITORING_AGGREGATED = '/monitoring/{pipeline_id}/metrics/aggregated'

    # Reports Routes
    REPORTS_LIST = '/reports'
    REPORTS_CREATE = '/reports'
    REPORTS_GET = '/reports/{report_id}'
    REPORTS_UPDATE = '/reports/{report_id}'
    REPORTS_DELETE = '/reports/{report_id}'
    REPORTS_STATUS = '/reports/{report_id}/status'
    REPORTS_EXPORT = '/reports/{report_id}/export'
    REPORTS_SCHEDULE = '/reports/schedule'
    REPORTS_METADATA = '/reports/{report_id}/metadata'
    REPORTS_PREVIEW = '/reports/{report_id}/preview'
    REPORTS_TEMPLATES = '/reports/templates'

    # Recommendations Routes
    RECOMMENDATIONS_LIST = '/recommendations'
    RECOMMENDATIONS_GET = '/recommendations/{recommendation_id}'
    RECOMMENDATIONS_APPLY = '/recommendations/{recommendation_id}/apply'
    RECOMMENDATIONS_STATUS = '/recommendations/{recommendation_id}/status'
    RECOMMENDATIONS_DISMISS = '/recommendations/{recommendation_id}/dismiss'
    RECOMMENDATIONS_HISTORY = '/recommendations/pipeline/{pipeline_id}/history'

    # Decisions Routes
    DECISIONS_LIST = '/decisions'
    DECISIONS_GET = '/decisions/{decision_id}'
    DECISIONS_MAKE = '/decisions/{decision_id}/make'
    DECISIONS_DEFER = '/decisions/{decision_id}/defer'
    DECISIONS_HISTORY = '/decisions/pipeline/{pipeline_id}/history'
    DECISIONS_IMPACT = '/decisions/{decision_id}/options/{option_id}/impact'

    # Settings Routes
    SETTINGS_PROFILE = '/settings/profile'
    SETTINGS_PREFERENCES = '/settings/preferences'
    SETTINGS_SECURITY = '/settings/security'
    SETTINGS_NOTIFICATIONS = '/settings/notifications'
    SETTINGS_APPEARANCE = '/settings/appearance'
    SETTINGS_VALIDATE = '/settings/validate'
    SETTINGS_RESET = '/settings/reset'

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
            '/pipeline/123/status'
        """
        route = cls[route_name].value
        return route.format(**kwargs) if kwargs else route