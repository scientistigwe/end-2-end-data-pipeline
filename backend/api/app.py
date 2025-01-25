# backend/flask_app.py

from flask import Flask, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import logging
import asyncio
from pathlib import Path
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine, text

# Import configurations
from config import get_config, db_config, config_manager

# Import middleware
from api.flask_app.middleware.auth_middleware import auth_middleware
from api.flask_app.middleware.logging import RequestLoggingMiddleware
from api.flask_app.middleware.error_handler import register_error_handlers

# Import core components
from core.messaging.broker import MessageBroker
from core.control.cpm import ControlPointManager
from core.staging.staging_manager import StagingManager

# Import repositories
from db.repository.staging_repository import StagingRepository
from db.repository.pipeline_repository import PipelineRepository

# Import services
from core.services import (
    AuthService, PipelineService, QualityService, InsightService,
    RecommendationService, DecisionService, MonitoringService,
    ReportService, SettingsService, AnalyticsService
)
from core.managers import (
    PipelineManager, QualityManager, InsightManager,
    RecommendationManager, DecisionManager, MonitoringManager,
    ReportManager, AnalyticsManager
)
from data.source import (
    FileService, DatabaseService as DBService,
    APIService, S3Service, StreamService
)
from core.services.staging.staging_service import StagingService

# Import route handling
from api.flask_app.utils.route_registry import normalize_route, APIRoutes
from api.flask_app.blueprints import create_blueprints

logger = logging.getLogger(__name__)


class ApplicationFactory:
    """Central application factory for creating and configuring Flask application."""

    def __init__(self):
        self.app = None
        self.components = {}
        self.services = {}
        self.async_loop = None
        self.logger = logging.getLogger(__name__)

    def _init_async_loop(self):
        """Initialize async loop for async operations."""
        try:
            self.async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.async_loop)
        except Exception as e:
            self.logger.error(f"Failed to initialize async loop: {str(e)}")
            raise

    def _configure_paths(self) -> None:
        """Configure application paths."""
        try:
            paths = [
                self.app.config['UPLOAD_FOLDER'],
                self.app.config['LOG_FOLDER'],
                self.app.config['STAGING_FOLDER']
            ]
            for path in paths:
                Path(path).mkdir(parents=True, exist_ok=True)
            self.logger.info("Application paths configured successfully")
        except Exception as e:
            self.logger.error(f"Path configuration failed: {str(e)}")
            raise

    def _configure_logging(self) -> None:
        """Configure application logging."""
        try:
            log_dir = Path(self.app.config['LOG_FOLDER'])
            log_dir.mkdir(parents=True, exist_ok=True)

            # Clear existing handlers and configure root logger
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)

            logging.basicConfig(
                level=self.app.config.get('LOG_LEVEL', logging.INFO),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

            # Setup handlers
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

            file_handler = logging.FileHandler(log_dir / self.app.config['LOG_FILENAME'])
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.INFO)

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.INFO)

            # Configure backend logger
            backend_logger = logging.getLogger('backend')
            backend_logger.setLevel(logging.INFO)
            backend_logger.propagate = False
            backend_logger.addHandler(file_handler)
            backend_logger.addHandler(console_handler)

            self.logger.info("Logging configured successfully")
        except Exception as e:
            self.logger.error(f"Logging configuration failed: {str(e)}")
            raise

    def _setup_database(self) -> scoped_session:
        """Initialize database connection and session."""
        try:
            # Use the database configuration from db_config
            engine, db_session = db_config.init_db()

            self.components['db_engine'] = engine
            self.components['db_session'] = db_session

            # Store on flask_app for blueprint access
            self.app.db = type('DB', (), {
                'session': db_session,
                'engine': engine
            })

            @self.app.teardown_appcontext
            def cleanup_db_session(exception=None):
                db_session.remove()

            self.logger.info("Database initialized successfully")
            return db_session

        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
            raise

    async def _init_core_components(self, db_session: scoped_session) -> None:
        """Initialize core application components."""
        try:
            # Initialize repositories
            staging_repo = StagingRepository(db_session)

            # Initialize message broker
            message_broker = MessageBroker()
            self.components['message_broker'] = message_broker

            # Initialize staging manager
            staging_manager = StagingManager(
                message_broker=message_broker,
                staging_repository=staging_repo,
                db_session=db_session,
                base_path=self.app.config['STAGING_FOLDER']
            )

            # Initialize CPM with staging manager
            cpm = ControlPointManager(
                message_broker=message_broker,
                staging_manager=staging_manager  # Pass staging_manager, not staging_repo
            )
            self.components['control_point_manager'] = cpm

            staging_manager = StagingManager(
                message_broker=message_broker,
                staging_repository=staging_repo,
                db_session=db_session,
                base_path=self.app.config['STAGING_FOLDER']
            )
            self.components['staging_manager'] = staging_manager

            # Start async components
            await asyncio.gather(
                cpm.initialize(),
                staging_manager.initialize()
            )

            self.logger.info("Core components initialized successfully")
        except Exception as e:
            self.logger.error(f"Core component initialization failed: {str(e)}")
            raise

    def _initialize_services(self, db_session: scoped_session) -> None:
        """
        Initialize all application services and their corresponding managers.
        This includes core system managers, analytical pipeline managers, and
        supporting service managers.
        """
        try:
            # Get core components
            message_broker = self.components['message_broker']
            staging_manager = self.components['staging_manager']
            cpm = self.components['control_point_manager']

            # Initialize repositories
            staging_repo = StagingRepository(db_session)
            pipeline_repo = PipelineRepository(db_session)

            # Initialize all system managers
            managers = {
                # Analytical Pipeline Managers
                'quality_manager': QualityManager(
                    message_broker=message_broker
                ),
                'insight_manager': InsightManager(
                    message_broker=message_broker
                ),
                'advanced_analytics_manager': AnalyticsManager(
                    message_broker=message_broker
                ),

                # Process Control Managers
                'pipeline_manager': PipelineManager(
                    message_broker=message_broker,
                    repository=pipeline_repo,
                    staging_manager=staging_manager,
                    control_point_manager=cpm
                ),
                'decision_manager': DecisionManager(
                    message_broker=message_broker
                ),

                # Support Managers
                'recommendation_manager': RecommendationManager(
                    message_broker=message_broker
                ),
                'report_manager': ReportManager(
                    message_broker=message_broker
                ),
                'monitoring_manager': MonitoringManager(
                    message_broker=message_broker,
                    db_session=db_session
                )
            }

            # Register managers as components
            self.components.update(managers)

            # Initialize all services with their corresponding managers
            self.services.update({
                # Core Services
                'auth_service': AuthService(db_session),

                # Data Source Services
                'file_service': FileService(
                    message_broker=message_broker,
                    staging_manager=staging_manager,
                    cpm=cpm,
                    config=self.app.config.get('FILE_SERVICE_CONFIG')
                ),
                'db_service': DBService(
                    message_broker=message_broker,
                    staging_manager=staging_manager,
                    cpm=cpm,
                    config=self.app.config.get('DB_SERVICE_CONFIG')
                ),
                'api_service': APIService(
                    message_broker=message_broker,
                    staging_manager=staging_manager,
                    cpm=cpm,
                    config=self.app.config.get('API_SERVICE_CONFIG')
                ),
                's3_service': S3Service(
                    message_broker=message_broker,
                    staging_manager=staging_manager,
                    cpm=cpm,
                    config=self.app.config.get('S3_SERVICE_CONFIG')
                ),
                'stream_service': StreamService(
                    message_broker=message_broker,
                    staging_manager=staging_manager,
                    cpm=cpm,
                    config=self.app.config.get('STREAM_SERVICE_CONFIG')
                ),

                # Analytical Services with Manager Dependencies
                'quality_service': QualityService(
                    manager=managers['quality_manager'],
                    message_broker=message_broker,
                    staging_manager=staging_manager
                ),
                'insight_service': InsightService(
                    manager=managers['insight_manager'],
                    message_broker=message_broker,
                    staging_manager=staging_manager
                ),
                'analytics_service': AnalyticsService(
                    manager=managers['advanced_analytics_manager'],
                    message_broker=message_broker,
                    staging_manager=staging_manager
                ),

                # Process Control Services
                'pipeline_service': PipelineService(
                    manager=managers['pipeline_manager'],
                    message_broker=message_broker,
                    staging_manager=staging_manager
                ),
                'decision_service': DecisionService(
                    manager=managers['decision_manager'],
                    message_broker=message_broker,
                    staging_manager=staging_manager
                ),

                # Support Services
                'recommendation_service': RecommendationService(
                    manager=managers['recommendation_manager'],
                    message_broker=message_broker,
                    staging_manager=staging_manager
                ),
                'monitoring_service': MonitoringService(
                    manager=managers['monitoring_manager'],
                    message_broker=message_broker,
                    staging_manager=staging_manager
                ),
                'report_service': ReportService(
                    manager=managers['report_manager'],
                    message_broker=message_broker,
                    staging_manager=staging_manager
                ),
                'settings_service': SettingsService(
                    staging_manager=staging_manager,
                    message_broker=message_broker
                ),

                # System Services
                'staging_manager': staging_manager,
                'staging_service': StagingService(
                    staging_manager=staging_manager,
                    staging_repository=staging_repo,
                    message_broker=message_broker
                )
            })

            # Store services on flask_app for access
            self.app.services = self.services
            self.logger.info("Services and managers initialized successfully")

        except Exception as e:
            self.logger.error(f"Service initialization failed: {str(e)}")
            raise

    def _setup_extensions(self) -> None:
        """Initialize Flask extensions."""
        try:
            # Setup CORS
            CORS(self.app, resources={r"/api/*": self.app.config['CORS_SETTINGS']})

            # Setup JWT
            jwt = JWTManager(self.app)

            @self.app.after_request
            def after_request(response):
                if request.method == 'OPTIONS':
                    response.status_code = 200
                    headers = {
                        'Access-Control-Allow-Origin': self.app.config['CORS_SETTINGS']['origins'][0],
                        'Access-Control-Allow-Methods': ', '.join(self.app.config['CORS_SETTINGS']['methods']),
                        'Access-Control-Allow-Headers': ', '.join(self.app.config['CORS_SETTINGS']['allow_headers']),
                        'Access-Control-Allow-Credentials': 'true',
                        'Access-Control-Max-Age': '3600'
                    }
                    response.headers.update(headers)
                return response

            self.logger.info("Extensions initialized successfully")
        except Exception as e:
            self.logger.error(f"Extension initialization failed: {str(e)}")
            raise

    def _register_routes(self) -> None:
        """Register all application routes and blueprints."""
        try:
            create_blueprints(self.app, self.services)
            self.logger.info("Routes registered successfully")
        except Exception as e:
            self.logger.error(f"Route registration failed: {str(e)}")
            raise

    def _register_health_check(self) -> None:
        """Register health check endpoint."""

        @self.app.route("/api/v1/health")
        def health_check():
            try:
                with self.app.db.session.begin():
                    self.app.db.session.execute(text("SELECT 1"))
                db_status = 'connected'
            except Exception as e:
                self.logger.error(f"Health check failed: {str(e)}")
                db_status = 'disconnected'

            return {
                'status': 'healthy',
                'db': db_status,
                'environment': self.app.config['ENV'],
                'components': {
                    name: 'healthy' for name in self.components
                }
            }

    def _register_error_handlers(self) -> None:
        """Register application error handlers."""
        register_error_handlers(self.app)

    def _cleanup(self) -> None:
        """Clean up all application components."""
        try:
            for name, component in reversed(list(self.components.items())):
                try:
                    if hasattr(component, 'cleanup'):
                        if asyncio.iscoroutinefunction(component.cleanup):
                            if self.async_loop and not self.async_loop.is_closed():
                                self.async_loop.run_until_complete(component.cleanup())
                        else:
                            component.cleanup()
                except Exception as e:
                    self.logger.error(f"Failed to clean up {name}: {str(e)}")

            if self.async_loop and not self.async_loop.is_closed():
                self.async_loop.close()

        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")

    def create_app(self, config_name: str = 'development') -> Flask:
        """Create and configure the Flask application."""
        try:
            # Initialize Flask app
            self.app = Flask(__name__)

            # Load configuration using new config system
            app_config = get_config(config_name)
            self.app.config.from_object(app_config)

            # Initialize database configuration
            db_config.app_config = app_config

            # Rest of your initialization code remains the same
            self._init_async_loop()
            self._configure_paths()
            self._configure_logging()
            self._setup_extensions()

            # Database and components
            db_session = self._setup_database()

            # Run async initialization in the event loop
            self.async_loop.run_until_complete(self._init_core_components(db_session))

            self._initialize_services(db_session)

            # Routes and middleware
            self._register_routes()
            self._register_health_check()
            self._register_error_handlers()

            # Add middleware
            self.app.wsgi_app = RequestLoggingMiddleware(self.app.wsgi_app)
            self.app.before_request(auth_middleware())

            # Register cleanup
            @self.app.teardown_appcontext
            def cleanup_context(exception=None):
                self._cleanup()

            self.logger.info(f"Application initialized successfully in {config_name} mode")
            return self.app

        except Exception as e:
            self.logger.error(f"Application creation failed: {str(e)}")
            self._cleanup()
            raise

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        app = loop.run_until_complete(ApplicationFactory().create_app('development'))
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        loop.close()
