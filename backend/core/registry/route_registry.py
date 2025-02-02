from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class HttpMethod(Enum):
    """HTTP methods supported by the API."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


@dataclass
class RouteInfo:
    """Information about a specific route."""
    path: str
    method: HttpMethod
    endpoint: str
    description: str
    requires_auth: bool = False
    required_role: Optional[str] = None
    parameters: Optional[Dict] = None
    response_schema: Optional[str] = None
    error_responses: Optional[Dict] = None


class RouteRegistry:
    """Centralized registry for all API routes."""

    def __init__(self):
        self._routes: Dict[str, List[RouteInfo]] = {}
        self._initialize_routes()

    def _initialize_routes(self):
        """Initialize all API routes."""
        # Authentication Routes
        self._register_auth_routes()
        # Core Routes
        self._register_pipeline_routes()
        # Analytics Routes
        self._register_analytics_routes()
        # Data Processing Routes
        self._register_data_processing_routes()
        # Data Source Routes
        self._register_data_source_routes()
        # Staging Routes
        self._register_staging_routes()
        # Monitoring Routes
        self._register_monitoring_routes()
        # Recommendations Routes
        self._register_recommendation_routes()
        # Decisions Routes
        self._register_decision_routes()
        # Reports Routes
        self._register_report_routes()
        # Insights Routes
        self._register_insight_routes()

    def _register_auth_routes(self):
        """Register authentication related routes."""
        auth_routes = [
            RouteInfo(
                path="/auth/register",
                method=HttpMethod.POST,
                endpoint="auth.register",
                description="Register a new user",
                parameters={
                    "email": "string",
                    "password": "string",
                    "name": "string"
                },
                response_schema="RegisterResponseSchema",
                error_responses={
                    409: "Email already registered",
                    400: "Validation error"
                }
            ),
            RouteInfo(
                path="/auth/login",
                method=HttpMethod.POST,
                endpoint="auth.login",
                description="Authenticate user and issue tokens",
                parameters={
                    "email": "string",
                    "password": "string",
                    "mfa_code": "string (optional)",
                    "remember_me": "boolean (optional)"
                },
                response_schema="LoginResponseSchema"
            ),
            RouteInfo(
                path="/auth/mfa/setup",
                method=HttpMethod.POST,
                endpoint="auth.setup_mfa",
                description="Set up multi-factor authentication",
                requires_auth=True,
                response_schema="MFASetupResponseSchema"
            ),
            RouteInfo(
                path="/auth/refresh",
                method=HttpMethod.POST,
                endpoint="auth.refresh_token",
                description="Refresh access token",
                requires_auth=True,
                response_schema="TokenResponseSchema"
            ),
            RouteInfo(
                path="/auth/logout",
                method=HttpMethod.POST,
                endpoint="auth.logout",
                description="Log out user",
                requires_auth=True
            ),
            RouteInfo(
                path="/auth/profile",
                method=HttpMethod.GET,
                endpoint="auth.get_profile",
                description="Get user profile",
                requires_auth=True,
                response_schema="UserProfileSchema"
            ),
            RouteInfo(
                path="/auth/profile",
                method=HttpMethod.PUT,
                endpoint="auth.update_profile",
                description="Update user profile",
                requires_auth=True,
                response_schema="UpdateProfileResponseSchema"
            ),
            RouteInfo(
                path="/auth/password/forgot",
                method=HttpMethod.POST,
                endpoint="auth.forgot_password",
                description="Initiate password reset process",
                response_schema="PasswordResetResponseSchema"
            ),
            RouteInfo(
                path="/auth/password/reset",
                method=HttpMethod.POST,
                endpoint="auth.reset_password",
                description="Reset password using reset token",
                response_schema="PasswordResetResponseSchema"
            ),
            RouteInfo(
                path="/auth/email/verify",
                method=HttpMethod.POST,
                endpoint="auth.verify_email",
                description="Verify email address",
                response_schema="EmailVerificationResponseSchema"
            )
        ]
        self._routes["auth"] = auth_routes

    def _register_pipeline_routes(self):
        """Register pipeline management routes."""
        pipeline_routes = [
            RouteInfo(
                path="/pipeline",
                method=HttpMethod.GET,
                endpoint="pipeline.list_pipelines",
                description="List pipelines with filtering and pagination",
                requires_auth=True,
                parameters={
                    "page": "integer (optional)",
                    "per_page": "integer (optional)",
                    "filters": "dict (optional)"
                },
                response_schema="PipelineListResponseSchema"
            ),
            RouteInfo(
                path="/pipeline",
                method=HttpMethod.POST,
                endpoint="pipeline.create_pipeline",
                description="Create new pipeline",
                requires_auth=True,
                response_schema="PipelineResponseSchema"
            ),
            RouteInfo(
                path="/pipeline/<pipeline_id>",
                method=HttpMethod.GET,
                endpoint="pipeline.get_pipeline",
                description="Get pipeline details",
                requires_auth=True,
                response_schema="PipelineResponseSchema"
            ),
            RouteInfo(
                path="/pipeline/<pipeline_id>/start",
                method=HttpMethod.POST,
                endpoint="pipeline.start_pipeline",
                description="Start pipeline execution",
                requires_auth=True,
                required_role="operator",
                response_schema="PipelineResponseSchema"
            ),
            RouteInfo(
                path="/pipeline/<pipeline_id>/status",
                method=HttpMethod.GET,
                endpoint="pipeline.get_pipeline_status",
                description="Get pipeline status",
                requires_auth=True,
                response_schema="PipelineStatusResponseSchema"
            ),
            RouteInfo(
                path="/pipeline/<pipeline_id>/logs",
                method=HttpMethod.GET,
                endpoint="pipeline.get_pipeline_logs",
                description="Get pipeline logs",
                requires_auth=True,
                response_schema="PipelineLogsResponseSchema"
            )
        ]
        self._routes["pipeline"] = pipeline_routes

    def _register_analytics_routes(self):
        """Register analytics processing routes."""
        analytics_routes = [
            RouteInfo(
                path="/analytics/quality/analyze",
                method=HttpMethod.POST,
                endpoint="analytics.quality_analyze",
                description="Start quality analysis",
                requires_auth=True,
                required_role="analyst",
                response_schema="QualityCheckResponseSchema"
            ),
            RouteInfo(
                path="/analytics/quality/<analysis_id>/status",
                method=HttpMethod.GET,
                endpoint="analytics.quality_status",
                description="Get quality analysis status",
                requires_auth=True,
                response_schema="QualityCheckResponseSchema"
            ),
            RouteInfo(
                path="/analytics/start",
                method=HttpMethod.POST,
                endpoint="analytics.start_analytics",
                description="Start analytics processing",
                requires_auth=True,
                required_role="analyst",
                response_schema="AnalyticsStagingResponseSchema"
            ),
            RouteInfo(
                path="/analytics/<job_id>/model",
                method=HttpMethod.GET,
                endpoint="analytics.get_model_details",
                description="Get trained model details",
                requires_auth=True,
                response_schema="AnalyticsStagingResponseSchema"
            )
        ]
        self._routes["analytics"] = analytics_routes

    def _register_data_source_routes(self):
        """Register data source management routes."""
        data_source_routes = [
            RouteInfo(
                path="/data-sources",
                method=HttpMethod.GET,
                endpoint="data_sources.list_sources",
                description="List all data sources",
                requires_auth=True
            ),
            RouteInfo(
                path="/data-sources",
                method=HttpMethod.POST,
                endpoint="data_sources.create_source",
                description="Create a new data source",
                requires_auth=True
            ),
            RouteInfo(
                path="/data-sources/<source_id>",
                method=HttpMethod.GET,
                endpoint="data_sources.get_source",
                description="Get data source details",
                requires_auth=True
            ),
            RouteInfo(
                path="/data-sources/<source_id>/preview",
                method=HttpMethod.GET,
                endpoint="data_sources.preview_source",
                description="Preview data from source",
                requires_auth=True,
                parameters={
                    "limit": "integer (optional)",
                    "offset": "integer (optional)",
                    "filters": "dict (optional)"
                }
            ),
            RouteInfo(
                path="/data-sources/db/connect",
                method=HttpMethod.POST,
                endpoint="data_sources.connect_database",
                description="Connect to database",
                requires_auth=True,
                response_schema="DatabaseSourceResponseSchema"
            ),
            RouteInfo(
                path="/data-sources/s3/connect",
                method=HttpMethod.POST,
                endpoint="data_sources.connect_s3",
                description="Connect to S3 bucket",
                requires_auth=True,
                response_schema="S3SourceResponseSchema"
            )
        ]
        self._routes["data_sources"] = data_source_routes

    def _register_staging_routes(self):
        """Register staging system routes."""
        staging_routes = [
            RouteInfo(
                path="/staging/outputs",
                method=HttpMethod.GET,
                endpoint="staging.list_outputs",
                description="List staged outputs",
                requires_auth=True,
                parameters={
                    "page": "integer (optional)",
                    "per_page": "integer (optional)",
                    "component_type": "string (optional)"
                }
            ),
            RouteInfo(
                path="/staging/outputs/<output_id>",
                method=HttpMethod.GET,
                endpoint="staging.get_output",
                description="Get staged output",
                requires_auth=True
            ),
            RouteInfo(
                path="/staging/outputs/<output_id>/archive",
                method=HttpMethod.POST,
                endpoint="staging.archive_output",
                description="Archive staged output",
                requires_auth=True,
                parameters={
                    "ttl_days": "integer (optional)",
                    "reason": "string (optional)"
                }
            ),
            RouteInfo(
                path="/staging/metrics",
                method=HttpMethod.GET,
                endpoint="staging.get_metrics",
                description="Get staging metrics",
                requires_auth=True
            )
        ]
        self._routes["staging"] = staging_routes

    def _register_monitoring_routes(self):
        """Register monitoring system routes."""
        monitoring_routes = [
            RouteInfo(
                path="/monitoring/<pipeline_id>/metrics",
                method=HttpMethod.POST,
                endpoint="monitoring.collect_metrics",
                description="Collect pipeline metrics",
                requires_auth=True,
                parameters={
                    "metrics": "list[str]",
                    "time_window": "string",
                    "aggregation": "string (optional)"
                },
                response_schema="MonitoringStagingResponseSchema"
            ),
            RouteInfo(
                path="/monitoring/<pipeline_id>/alerts/configure",
                method=HttpMethod.POST,
                endpoint="monitoring.configure_alerts",
                description="Configure alert rules",
                requires_auth=True,
                response_schema="AlertStagingResponseSchema"
            ),
            RouteInfo(
                path="/monitoring/<pipeline_id>/performance",
                method=HttpMethod.GET,
                endpoint="monitoring.get_performance_metrics",
                description="Get performance metrics",
                requires_auth=True
            )
        ]
        self._routes["monitoring"] = monitoring_routes

    def _register_recommendation_routes(self):
        """Register recommendation system routes."""
        recommendation_routes = [
            RouteInfo(
                path="/recommendations/generate",
                method=HttpMethod.POST,
                endpoint="recommendations.generate_recommendations",
                description="Generate recommendations",
                requires_auth=True,
                response_schema="RecommendationStagingResponseSchema"
            ),
            RouteInfo(
                path="/recommendations/list",
                method=HttpMethod.GET,
                endpoint="recommendations.list_recommendations",
                description="List recommendations",
                requires_auth=True
            ),
            RouteInfo(
                path="/recommendations/<recommendation_id>/apply",
                method=HttpMethod.POST,
                endpoint="recommendations.apply_recommendation",
                description="Apply recommendation",
                requires_auth=True
            ),
            RouteInfo(
                path="/recommendations/<recommendation_id>/impact",
                method=HttpMethod.GET,
                endpoint="recommendations.analyze_impact",
                description="Analyze recommendation impact",
                requires_auth=True
            )
        ]
        self._routes["recommendations"] = recommendation_routes

    def _register_decision_routes(self):
        """Register decision management routes."""
        decision_routes = [
            RouteInfo(
                path="/decisions/<pipeline_id>/pending",
                method=HttpMethod.GET,
                endpoint="decisions.get_pending_decisions",
                description="Get pending decisions",
                requires_auth=True,
                response_schema="DecisionListResponseSchema"
            ),
            RouteInfo(
                path="/decisions/<decision_id>/make",
                method=HttpMethod.POST,
                endpoint="decisions.make_decision",
                description="Make a decision",
                requires_auth=True,
                response_schema="DecisionStagingResponseSchema"
            ),
            RouteInfo(
                path="/decisions/<decision_id>/feedback",
                method=HttpMethod.POST,
                endpoint="decisions.provide_feedback",
                description="Provide decision feedback",
                requires_auth=True
            )
        ]
        self._routes["decisions"] = decision_routes

    def _register_report_routes(self):
        """Register report generation routes."""
        report_routes = [
            RouteInfo(
                path="/reports/generate",
                method=HttpMethod.POST,
                endpoint="reports.generate_report",
                description="Generate report",
                requires_auth=True,
                response_schema="ReportStagingResponseSchema"
            ),
            RouteInfo(
                path="/reports/<generation_id>/download",
                method=HttpMethod.GET,
                endpoint="reports.download_report",
                description="Download report",
                requires_auth=True,
                parameters={
                    "format": "string (optional, default='pdf')"
                }
            ),
            RouteInfo(
                path="/reports/templates",
                method=HttpMethod.POST,
                endpoint="reports.create_template",
                description="Create report template",
                requires_auth=True
            ),
            RouteInfo(
                path="/reports/templates/<template_id>/preview",
                method=HttpMethod.GET,
                endpoint="reports.preview_template",
                description="Preview report template",
                requires_auth=True
            )
        ]
        self._routes["reports"] = report_routes

    def _register_insight_routes(self):
        """Register insight generation routes."""
        insight_routes = [
            RouteInfo(
                path="/insights/generate",
                method=HttpMethod.POST,
                endpoint="insights.generate_insights",
                description="Generate insights",
                requires_auth=True,
                response_schema="InsightStagingResponseSchema"
            ),
            RouteInfo(
                path="/insights/<generation_id>/status",
                method=HttpMethod.GET,
                endpoint="insights.get_generation_status",
                description="Get insight generation status",
                requires_auth=True,
                response_schema="InsightStagingResponseSchema"
            ),
            RouteInfo(
                path="/insights/<generation_id>/results",
                method=HttpMethod.GET,
                endpoint="insights.get_insights",
                description="Get generated insights",
                requires_auth=True,
                response_schema="InsightStagingResponseSchema"
            ),
            RouteInfo(
                path="/insights/<generation_id>/trends",
                method=HttpMethod.GET,
                endpoint="insights.get_trend_insights",
                description="Get trend-specific insights",
                requires_auth=True
            ),
            RouteInfo(
                path="/insights/<generation_id>/anomalies",
                method=HttpMethod.GET,
                endpoint="insights.get_anomaly_insights",
                description="Get anomaly insights",
                requires_auth=True
            ),
            RouteInfo(
                path="/insights/<generation_id>/correlations",
                method=HttpMethod.GET,
                endpoint="insights.get_correlation_insights",
                description="Get correlation insights",
                requires_auth=True
            ),
            RouteInfo(
                path="/insights/<generation_id>/validate",
                method=HttpMethod.POST,
                endpoint="insights.validate_insights",
                description="Validate generated insights",
                requires_auth=True
            )
        ]
        self._routes["insights"] = insight_routes

    def _register_data_processing_routes(self):
        """Register data processing routes."""
        data_processing_routes = [
            RouteInfo(
                path="/quality/analyze",
                method=HttpMethod.POST,
                endpoint="quality.quality_analyze_start",
                description="Initiate quality analysis",
                requires_auth=True,
                response_schema="QualityCheckResponseSchema"
            ),
            RouteInfo(
                path="/quality/<analysis_id>/status",
                method=HttpMethod.GET,
                endpoint="quality.get_analysis_status",
                description="Get quality analysis status",
                requires_auth=True,
                response_schema="QualityCheckResponseSchema"
            ),
            RouteInfo(
                path="/quality/<analysis_id>/results",
                method=HttpMethod.GET,
                endpoint="quality.get_analysis_results",
                description="Get quality analysis results",
                requires_auth=True,
                response_schema="QualityCheckResponseSchema"
            ),
            RouteInfo(
                path="/quality/<analysis_id>/issues",
                method=HttpMethod.GET,
                endpoint="quality.get_quality_issues",
                description="Get quality issues",
                requires_auth=True
            ),
            RouteInfo(
                path="/quality/<analysis_id>/remediation",
                method=HttpMethod.GET,
                endpoint="quality.get_remediation_plan",
                description="Get remediation plan",
                requires_auth=True
            ),
            RouteInfo(
                path="/quality/config/rules",
                method=HttpMethod.POST,
                endpoint="quality.update_validation_rules",
                description="Update validation rules",
                requires_auth=True
            )
        ]
        self._routes["quality"] = data_processing_routes

    # Helper methods for route access
    def get_routes_by_category(self, category: str) -> List[RouteInfo]:
        """Get all routes for a specific category."""
        return self._routes.get(category, [])

    def get_all_routes(self) -> Dict[str, List[RouteInfo]]:
        """Get all registered routes."""
        return self._routes

    def get_authenticated_routes(self) -> List[RouteInfo]:
        """Get all routes that require authentication."""
        auth_routes = []
        for routes in self._routes.values():
            auth_routes.extend([r for r in routes if r.requires_auth])
        return auth_routes

    def get_routes_by_role(self, role: str) -> List[RouteInfo]:
        """Get all routes that require a specific role."""
        role_routes = []
        for routes in self._routes.values():
            role_routes.extend([r for r in routes if r.required_role == role])
        return role_routes

    def get_routes_by_method(self, method: HttpMethod) -> List[RouteInfo]:
        """Get all routes with a specific HTTP method."""
        method_routes = []
        for routes in self._routes.values():
            method_routes.extend([r for r in routes if r.method == method])
        return method_routes

    def get_routes_with_schema(self, schema_name: str) -> List[RouteInfo]:
        """Get all routes that use a specific response schema."""
        schema_routes = []
        for routes in self._routes.values():
            schema_routes.extend([r for r in routes if r.response_schema == schema_name])
        return schema_routes