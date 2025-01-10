# backend/backend/flask_api/app.py
from flask import Flask, g, request, jsonify
from flask_cors import CORS
import logging
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from sqlalchemy import text

# Import configurations and database
from backend.config import get_config, init_db, cleanup_db

# Import middleware
from .middleware.auth_middleware import auth_middleware
from .middleware.logging import RequestLoggingMiddleware
from .middleware.error_handler import register_error_handlers

# Import core components
from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.pipeline_manager import PipelineManager

# Import route registry and response builder
from .utils.route_registry import APIRoutes, normalize_route
from .utils.response_builder import ResponseBuilder

# Import all services
from .services.auth.auth_service import AuthService
from .services.data_sources.file_source_service import FileSourceService
from .services.data_sources.api_service import APISourceService
from .services.data_sources.database_service import DatabaseSourceService
from .services.data_sources.s3_service import S3SourceService
from .services.data_sources.stream_service import StreamSourceService
from .services.pipeline.pipeline_service import PipelineService
from .services.analysis.quality_service import QualityService
from .services.analysis.insight_service import InsightService
from .services.decision_recommendation.recommendations_service import RecommendationService
from .services.decision_recommendation.decision_service import DecisionService
from .services.monitoring.monitoring_service import MonitoringService
from .services.reports.report_service import ReportService
from .services.settings.settings_service import SettingsService

logger = logging.getLogger(__name__)


class ApplicationFactory:
    """Factory class for creating and configuring Flask application instances."""

    def __init__(self):
        self.app: Flask = None
        self.services: Dict[str, Any] = {}
        self.components: Dict[str, Any] = {}
        self.response_builder = ResponseBuilder()

    def _initialize_cors(self) -> None:
        """Initialize CORS with proper settings."""
        try:
            CORS(
                self.app,
                resources={
                    r"/api/*": self.app.config['CORS_SETTINGS']
                }
            )

            @self.app.after_request
            def after_request(response):
                if request.method == 'OPTIONS':
                    headers = {
                        'Access-Control-Allow-Origin': self.app.config['CORS_SETTINGS']['origins'][0],
                        'Access-Control-Allow-Methods': ', '.join(self.app.config['CORS_SETTINGS']['methods']),
                        'Access-Control-Allow-Headers': ', '.join(self.app.config['CORS_SETTINGS']['allow_headers']),
                        'Access-Control-Allow-Credentials': 'true',
                        'Access-Control-Max-Age': '3600'
                    }
                    response.headers.update(headers)
                return response

            logger.info("CORS initialized successfully")
        except Exception as e:
            logger.error(f"CORS initialization error: {str(e)}", exc_info=True)
            raise

    def _initialize_components(self) -> None:
        """Initialize application components."""
        try:
            logger.info("Starting component initialization...")

            # Initialize MessageBroker with config
            max_workers = self.app.config.get('PIPELINE_MAX_WORKERS', 4)
            message_broker = MessageBroker(max_workers=max_workers)
            self.components['message_broker'] = message_broker
            logger.debug("MessageBroker initialized")

            # Initialize PipelineManager
            pipeline_manager = PipelineManager(
                message_broker=message_broker,
                db_session=self.app.db
            )
            self.components['pipeline_manager'] = pipeline_manager
            logger.debug("PipelineManager initialized")

            logger.info("Components initialized successfully")
        except Exception as e:
            logger.error(f"Component initialization error: {str(e)}", exc_info=True)
            raise

    def _initialize_services(self, db_session) -> None:
        """Initialize all application services with dependencies."""
        try:
            logger.info("Starting services initialization...")

            # Get required components
            message_broker = self.components.get('message_broker')
            pipeline_manager = self.components.get('pipeline_manager')

            if not message_broker or not pipeline_manager:
                raise ValueError("Required components not initialized")

            # Initialize all services
            self.services = {
                'auth_service': AuthService(db_session),
                'file_service': FileSourceService(
                    db_session,
                    allowed_extensions=self.app.config['ALLOWED_EXTENSIONS'],
                    max_file_size=self.app.config['MAX_CONTENT_LENGTH']
                ),
                'db_service': DatabaseSourceService(db_session),
                's3_service': S3SourceService(db_session),
                'api_service': APISourceService(db_session),
                'stream_service': StreamSourceService(db_session),
                'pipeline_service': PipelineService(
                    db_session=db_session,
                    message_broker=message_broker,
                    pipeline_manager=pipeline_manager
                ),
                'quality_service': QualityService(db_session),
                'insight_service': InsightService(db_session),
                'recommendation_service': RecommendationService(db_session),
                'decision_service': DecisionService(db_session),
                'monitoring_service': MonitoringService(db_session),
                'report_service': ReportService(db_session),
                'settings_service': SettingsService(db_session)
            }

            # Store services in app context
            self.app.services = self.services
            logger.info("All services initialized successfully")
        except Exception as e:
            logger.error(f"Service initialization error: {str(e)}", exc_info=True)
            raise

    def _register_blueprints(self, db_session) -> None:
        """Register all application blueprints using route registry."""
        try:
            logger.info("Starting blueprint registration...")

            # Import blueprints
            from .blueprints.auth.routes import create_auth_blueprint
            from .blueprints.data_sources.routes import create_data_source_blueprint
            from .blueprints.pipeline.routes import create_pipeline_blueprint
            from .blueprints.analysis.routes import create_analysis_blueprint
            from .blueprints.recommendations.routes import create_recommendation_blueprint
            from .blueprints.decisions.routes import create_decision_blueprint
            from .blueprints.monitoring.routes import create_monitoring_blueprint
            from .blueprints.reports.routes import create_reports_blueprint
            from .blueprints.settings.routes import create_settings_blueprint

            # Define blueprints with routes from registry
            blueprints = [
                (create_auth_blueprint(self.services['auth_service'], db_session),
                 normalize_route(APIRoutes.AUTH_LOGIN.value.path).rsplit('/', 1)[0]),

                (create_data_source_blueprint(
                    self.services['file_service'],
                    self.services['db_service'],
                    self.services['s3_service'],
                    self.services['api_service'],
                    self.services['stream_service'],
                    db_session
                ), normalize_route(APIRoutes.DATASOURCE_LIST.value.path)),

                (create_pipeline_blueprint(self.services['pipeline_service'], db_session),
                 normalize_route(APIRoutes.PIPELINE_LIST.value.path).rsplit('/', 1)[0]),

                (create_analysis_blueprint(
                    self.services['quality_service'],
                    self.services['insight_service'],
                    db_session
                ), normalize_route(APIRoutes.ANALYSIS_QUALITY_START.value.path).rsplit('/', 2)[0]),

                (create_recommendation_blueprint(self.services['recommendation_service'], db_session),
                 normalize_route(APIRoutes.RECOMMENDATIONS_LIST.value.path)),

                (create_decision_blueprint(self.services['decision_service'], db_session),
                 normalize_route(APIRoutes.DECISIONS_LIST.value.path)),

                (create_monitoring_blueprint(self.services['monitoring_service'], db_session),
                 normalize_route(APIRoutes.MONITORING_START.value.path).rsplit('/', 2)[0]),

                (create_reports_blueprint(self.services['report_service'], db_session),
                 normalize_route(APIRoutes.REPORTS_LIST.value.path)),

                (create_settings_blueprint(self.services['settings_service'], db_session),
                 normalize_route(APIRoutes.SETTINGS_PROFILE.value.path).rsplit('/', 1)[0])
            ]

            # Register blueprints
            for blueprint, url_prefix in blueprints:
                self.app.register_blueprint(blueprint, url_prefix=f"/api/v1{url_prefix}")
                logger.debug(f"Registered blueprint at /api/v1{url_prefix}")

            logger.info("All blueprints registered successfully")
        except Exception as e:
            logger.error(f"Blueprint registration error: {str(e)}", exc_info=True)
            raise

    def _register_health_check(self) -> None:
        """Register health check endpoint."""

        @self.app.route("/api/v1/health")
        def health_check():
            try:
                with self.app.db.begin() as session:
                    session.execute(text("SELECT 1"))
                db_status = 'connected'
            except Exception as e:
                logger.error(f"Database health check failed: {e}")
                db_status = 'disconnected'

            return self.response_builder.success(
                data={
                    'status': 'healthy',
                    'database': db_status,
                    'environment': self.app.config['ENV']
                }
            )

    def _register_cleanup_handlers(self) -> None:
        """Register cleanup handlers for application shutdown."""
        try:
            @self.app.teardown_appcontext
            def cleanup_services(exception=None):
                try:
                    # Cleanup message broker
                    if hasattr(self.app, 'message_broker'):
                        self.app.message_broker.cleanup()

                    # Cleanup pipeline manager
                    if hasattr(self.app, 'pipeline_manager'):
                        if hasattr(self.app.pipeline_manager, 'cleanup'):
                            self.app.pipeline_manager.cleanup()
                        elif hasattr(self.app.pipeline_manager, '_cleanup_all_pipelines'):
                            self.app.pipeline_manager._cleanup_all_pipelines()

                    # Cleanup database
                    if hasattr(self.app, 'engine'):
                        cleanup_db(self.app.engine)
                except Exception as e:
                    logger.error(f"Error during service cleanup: {str(e)}")

            logger.info("Cleanup handlers registered successfully")
        except Exception as e:
            logger.error(f"Error registering cleanup handlers: {str(e)}")
            raise

    def _cleanup_on_error(self) -> None:
        """Cleanup resources if initialization fails"""
        try:
            for component in self.components.values():
                if hasattr(component, 'cleanup'):
                    try:
                        component.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up component: {str(e)}")
        except Exception as e:
            logger.error(f"Error during error cleanup: {str(e)}")

    def create_app(self, config_name: str = 'development') -> Flask:
        """Create and configure the Flask application instance."""
        try:
            # Initialize Flask app and config
            self.app = Flask(__name__)
            self.app.config.from_object(get_config(config_name))

            # Initialize database first
            engine, db_session = init_db(self.app)
            self.app.db = db_session

            # Initialize core components
            self._initialize_cors()
            self._initialize_components()

            # Store components in app context
            self.app.message_broker = self.components.get('message_broker')
            self.app.pipeline_manager = self.components.get('pipeline_manager')

            # Initialize services and routes
            self._initialize_services(db_session)
            self._register_blueprints(db_session)
            self._register_health_check()

            # Register middleware and handlers
            self.app.wsgi_app = RequestLoggingMiddleware(self.app.wsgi_app)
            self.app.before_request(auth_middleware())
            register_error_handlers(self.app)
            self._register_cleanup_handlers()

            # Add response builder to app context
            self.app.response_builder = self.response_builder

            logger.info(f"Application initialized successfully in {config_name} mode")
            return self.app

        except Exception as e:
            logger.error(f"Failed to create application: {str(e)}", exc_info=True)
            self._cleanup_on_error()
            raise


def create_app(config_name: str = 'development') -> Flask:
    """Application factory function."""
    return ApplicationFactory().create_app(config_name)