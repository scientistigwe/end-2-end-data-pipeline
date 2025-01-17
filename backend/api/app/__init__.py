# api/app/__init__.py

from flask import Flask, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import logging
import asyncio
from pathlib import Path
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine

# Import configurations
from config import get_config

# Import middleware
from .middleware.error_handler import register_error_handlers
from .middleware.logging import RequestLoggingMiddleware
from .middleware.auth_middleware import auth_middleware
from .utils.route_registry import normalize_route, APIRoutes

# Import auth manager
from .auth.jwt_manager import JWTTokenManager

# Import all services
from .services.auth.auth_service import AuthService
from .services.pipeline.pipeline_service import PipelineService
from .services.analysis.quality_service import QualityService
from .services.analysis.insight_service import InsightService
from .services.decision_recommendation.recommendations_service import RecommendationService
from .services.decision_recommendation.decision_service import DecisionService
from .services.monitoring.monitoring_service import MonitoringService
from .services.reports.report_service import ReportService
from .services.settings.settings_service import SettingsService

# Import updated messaging components
from backend.core.messaging.broker import MessageBroker
from backend.core.control.control_point_manager import ControlPointManager
from backend.core.orchestration.staging_manager import StagingManager

from backend.db.repository.pipeline_repository import PipelineRepository

logger = logging.getLogger(__name__)

def configure_logging(app: Flask) -> None:
    """Configure application logging with proper handler configuration."""
    try:
        log_dir = Path(app.config['LOG_FOLDER'])
        log_dir.mkdir(parents=True, exist_ok=True)

        # Remove all existing handlers to avoid duplicates
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        # Configure root logger at WARNING level
        logging.basicConfig(
            level=logging.WARNING,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Create formatters
        standard_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Create and configure file handler
        file_handler = logging.FileHandler(log_dir / app.config['LOG_FILENAME'])
        file_handler.setFormatter(standard_formatter)
        file_handler.setLevel(logging.INFO)

        # Create and configure console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(standard_formatter)
        console_handler.setLevel(logging.INFO)

        # Configure backend logger specifically
        backend_logger = logging.getLogger('backend')
        backend_logger.setLevel(logging.INFO)
        backend_logger.propagate = False  # Prevent duplicate logs
        backend_logger.addHandler(file_handler)
        backend_logger.addHandler(console_handler)

        logger.info("Logging configured successfully")
    except Exception as e:
        print(f"Error configuring logging: {str(e)}")
        raise

def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions"""
    try:
        CORS(app, resources={r"/api/*": app.config['CORS_SETTINGS']})

        # Initialize JWT Manager
        jwt = JWTManager(app)

        @app.after_request
        def after_request(response):
            if request.method == 'OPTIONS':
                response.status_code = 200
                headers = {
                    'Access-Control-Allow-Origin': app.config['CORS_SETTINGS']['origins'][0],
                    'Access-Control-Allow-Credentials': str(
                        app.config['CORS_SETTINGS'].get('supports_credentials', 'false')).lower(),
                    'Access-Control-Allow-Methods': ', '.join(app.config['CORS_SETTINGS']['methods']),
                    'Access-Control-Allow-Headers': ', '.join(app.config['CORS_SETTINGS']['allow_headers']),
                    'Access-Control-Max-Age': '3600'
                }
                response.headers.update(headers)
            return response

        logger.info("Extensions initialized successfully")

    except Exception as e:
        logger.error(f"Extension initialization error: {str(e)}", exc_info=True)
        raise

def _configure_paths(app: Flask) -> None:
    """Configure application paths."""
    try:
        for folder in ['UPLOAD_FOLDER', 'LOG_FOLDER', 'TEMP_FOLDER', 'STAGING_FOLDER']:
            directory = Path(app.config.get(folder, ''))
            if directory:
                directory.mkdir(parents=True, exist_ok=True)

        logger.info("Application paths configured successfully")

    except Exception as e:
        logger.error(f"Path configuration error: {str(e)}", exc_info=True)
        raise

def _init_database(app: Flask) -> scoped_session:
    """Initialize db connection and session factory"""
    try:
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        session_factory = sessionmaker(bind=engine)
        session = scoped_session(session_factory)

        # Register session cleanup
        @app.teardown_appcontext
        def cleanup_db_session(exception=None):
            session.remove()

        return session

    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}", exc_info=True)
        raise


def _initialize_services(app: Flask, db_session: scoped_session) -> None:
    """Initialize all application services."""
    try:
        # Create event loop for async operations
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        except Exception as e:
            logger.warning(f"Could not create new event loop: {e}")
            loop = asyncio.get_event_loop()

        # Initialize MessageBroker
        message_broker = MessageBroker(
            max_workers=app.config.get('PIPELINE_MAX_WORKERS', 4)
        )

        # Initialize components
        pipeline_repository = PipelineRepository(db_session)

        # Initialize Control Point Manager
        control_point_manager = ControlPointManager(
            message_broker=message_broker
        )

        # Safely start message handlers
        try:
            control_point_manager.start_message_handlers()
        except Exception as e:
            logger.error(f"Error starting control point manager handlers: {e}")

        # Similarly for staging manager
        staging_manager = StagingManager(
            message_broker=message_broker,
            control_point_manager=control_point_manager
        )

        try:
            staging_manager.start_message_handlers()
        except Exception as e:
            logger.error(f"Error starting staging manager handlers: {e}")

        # Rest of the initialization remains the same...

    except Exception as e:
        logger.error(f"Service initialization error: {str(e)}")
        raise

def register_blueprints(message_broker: MessageBroker, app: Flask, db_session: scoped_session) -> None:
    """Register all application blueprints using route registry."""
    try:
        logger.info("Starting blueprint registration...")

        # Import services (this should be done before using them)
        from .services.auth.auth_service import AuthService
        from backend.data_pipeline.source.file.file_service import FileService
        from backend.data_pipeline.source.database.db_service import DBService
        from backend.data_pipeline.source.api.api_service import APIService
        from backend.data_pipeline.source.cloud.s3_service import S3Service
        from backend.data_pipeline.source.stream.stream_service import StreamService
        from .services.pipeline.pipeline_service import PipelineService
        from .services.analysis.quality_service import QualityService
        from .services.analysis.insight_service import InsightService
        from .services.decision_recommendation.recommendations_service import RecommendationService
        from .services.decision_recommendation.decision_service import DecisionService
        from .services.monitoring.monitoring_service import MonitoringService
        from .services.reports.report_service import ReportService
        from .services.settings.settings_service import SettingsService

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

        # Initialize services
        services = {
            'auth_service': AuthService(db_session),
            'file_service': FileService(message_broker),
            'db_service': DBService(message_broker),
            'api_service': APIService(message_broker),
            's3_service': S3Service(message_broker),
            'stream_service': StreamService(message_broker),
            'pipeline_service': PipelineService(
                message_broker=message_broker, 
                repository=PipelineRepository(db_session)
            ),
            'quality_service': QualityService(db_session),
            'insight_service': InsightService(db_session),
            'recommendation_service': RecommendationService(db_session),
            'decision_service': DecisionService(db_session),
            'monitoring_service': MonitoringService(db_session),
            'report_service': ReportService(db_session),
            'settings_service': SettingsService(db_session)
        }

        # Define blueprints with routes from registry
        blueprints = [
            (create_auth_blueprint(services['auth_service'], db_session),
             normalize_route(APIRoutes.AUTH_LOGIN.value.path).rsplit('/', 1)[0]),

            (create_data_source_blueprint(
                services['file_service'],
                services['db_service'],
                services['s3_service'],
                services['api_service'],
                services['stream_service']
            ), normalize_route(APIRoutes.DATASOURCE_LIST.value.path)),

            (create_pipeline_blueprint(services['pipeline_service'], db_session),
             normalize_route(APIRoutes.PIPELINE_LIST.value.path).rsplit('/', 1)[0]),

            (create_analysis_blueprint(
                services['quality_service'],
                services['insight_service'],
                db_session
            ), normalize_route(APIRoutes.ANALYSIS_QUALITY_START.value.path).rsplit('/', 2)[0]),

            (create_recommendation_blueprint(services['recommendation_service'], db_session),
             normalize_route(APIRoutes.RECOMMENDATIONS_LIST.value.path)),

            (create_decision_blueprint(services['decision_service'], db_session),
             normalize_route(APIRoutes.DECISIONS_LIST.value.path)),

            (create_monitoring_blueprint(services['monitoring_service'], db_session),
             normalize_route(APIRoutes.MONITORING_START.value.path).rsplit('/', 2)[0]),

            (create_reports_blueprint(services['report_service'], db_session),
             normalize_route(APIRoutes.REPORTS_LIST.value.path)),

            (create_settings_blueprint(services['settings_service'], db_session),
             normalize_route(APIRoutes.SETTINGS_PROFILE.value.path).rsplit('/', 1)[0])
        ]

        # Register blueprints
        for blueprint, url_prefix in blueprints:
            app.register_blueprint(blueprint, url_prefix=f"/api/v1{url_prefix}")
            logger.debug(f"Registered blueprint at /api/v1{url_prefix}")

        # Optional: Store services on the app object if you need to access them later
        app.services = services

        logger.info("All blueprints registered successfully")
    except Exception as e:
        logger.error(f"Blueprint registration error: {str(e)}", exc_info=True)
        raise

def register_health_check(self) -> None:
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
                'db': db_status,
                'environment': self.app.config['ENV']
            }
        )

def register_cleanup_handlers(self) -> None:
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

                # Cleanup db
                if hasattr(self.app, 'engine'):
                    cleanup_db(self.app.engine)
            except Exception as e:
                logger.error(f"Error during service cleanup: {str(e)}")

        logger.info("Cleanup handlers registered successfully")
    except Exception as e:
        logger.error(f"Error registering cleanup handlers: {str(e)}")
        raise

def cleanup_on_error(self) -> None:
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


def create_app(config_name: str = 'development') -> Flask:
    """Application factory function."""
    try:
        # Initialize Flask app
        app = Flask(__name__)

        # Load configuration
        app_config = get_config(config_name)
        app.config.from_object(app_config)

        # Configure logging first
        configure_logging(app)

        # Initialize db
        db_session = _init_database(app)

        # Initialize components in order
        _configure_paths(app)
        _init_extensions(app)

        # Initialize all services with db session
        with app.app_context():
            # Create message broker
            message_broker = MessageBroker(
                max_workers=app.config.get('PIPELINE_MAX_WORKERS', 4)
            )
            
            # Store message broker on app for later access
            app.message_broker = message_broker

            _initialize_services(app, db_session)

        # Register error handlers and blueprints
        register_error_handlers(app)
        with app.app_context():
            # Pass message_broker to register_blueprints
            register_blueprints(message_broker, app, db_session)

        # Add request logging middleware
        app.wsgi_app = RequestLoggingMiddleware(app.wsgi_app)

        # Add auth middleware
        app.before_request(auth_middleware())

        # Add cleanup on app context teardown
        @app.teardown_appcontext
        def cleanup_services(exception=None):
            if hasattr(app, 'message_broker'):
                app.message_broker.cleanup()
            if hasattr(app, 'control_point_manager'):
                # Perform any additional cleanup for control point manager
                pass
            if hasattr(app, 'staging_manager'):
                # Perform any additional cleanup for staging manager
                pass
            if hasattr(app, 'db_session'):
                app.db_session.remove()

        logger.info(f"Application initialized successfully in {config_name} mode")
        return app

    except Exception as e:
        logger.error(f"Failed to create application: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    app = create_app('development')
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )