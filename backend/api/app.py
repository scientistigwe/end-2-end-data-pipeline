# backend/api/app.py

import os
import logging
from typing import Dict, Any, Optional
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from sqlalchemy.orm import scoped_session

from flask import Flask, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from sqlalchemy import text

# Import configurations
from config.app_config import get_config
from config.database import DatabaseConfig

# Import middleware
from api.flask_app.middleware.auth_middleware import auth_middleware
from api.flask_app.middleware.logging import RequestLoggingMiddleware
from api.flask_app.middleware.error_handler import register_error_handlers

# Import core components
from core.messaging.broker import MessageBroker
from core.control.cpm import ControlPointManager
from core.messaging.event_types import (
    MessageType, ProcessingStage, ProcessingStatus, MessageMetadata,
    ComponentType, ModuleIdentifier
)

# Import repositories and services
from db.repository.staging_repository import StagingRepository
from db.repository.pipeline_repository import PipelineRepository
from core.services.staging.staging_service import StagingService
from core.managers import (
    QualityManager, InsightManager, AnalyticsManager, PipelineManager,
    DecisionManager, MonitoringManager, ReportManager, StagingManager,
    RecommendationManager
)
from core.services import (
    QualityService, InsightService, AnalyticsService,
    DecisionService, MonitoringService, ReportService,
    AuthService, PipelineService, RecommendationService
)
from data.source import (
    FileService, DatabaseService as DBService,
    APIService, S3Service, StreamService
)

from config.validation_config import ValidationConfigs

# Import route handling
from api.flask_app.blueprints import create_blueprints
from api.flask_app.auth.jwt_manager import JWTTokenManager

logger = logging.getLogger(__name__)


class ApplicationFactory:
    """Enhanced async application factory with proper component lifecycle management"""

    def __init__(self):
        self.app: Optional[Flask] = None
        self.components: Dict[str, Any] = {}
        self.services: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self.config = None
        self.db_config = None
        self.jwt_manager = None

    @asynccontextmanager
    async def lifespan_context(self, config_name: str):
        """Application lifespan context manager for async resources"""
        try:
            # First create Flask app and load config
            self.app = Flask(__name__)
            app_config = get_config(config_name)
            self.app.config.from_object(app_config)
            self.config = app_config  # Store config instance

            # Configure basic necessities first
            self._configure_paths()
            self._configure_logging()

            # Initialize database configuration
            self.db_config = DatabaseConfig(app_config=self.config)

            # Setup database before anything else
            db_session = self._setup_database()
            self.components['db_session'] = db_session

            # Setup extensions
            self._setup_extensions()

            # Initialize async resources
            await self._init_async_resources()

            # Finally setup routes and services
            self._initialize_services(db_session)
            self._register_routes()
            self._register_health_check()
            self._register_error_handlers()

            # Add middleware last
            self.app.wsgi_app = RequestLoggingMiddleware(self.app.wsgi_app)
            self.app.before_request(auth_middleware())

            yield
        finally:
            if self.db_config:
                self.db_config.cleanup()
            await self._cleanup_async_resources()

    def _configure_paths(self) -> None:
        """Configure application paths."""
        try:
            paths = [
                self.config.UPLOAD_FOLDER,
                self.config.LOG_FOLDER,
                self.config.STAGING_FOLDER
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
            log_dir = Path(self.config.LOG_FOLDER)
            log_dir.mkdir(parents=True, exist_ok=True)

            # Clear existing handlers
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)

            # Configure basic logging
            logging.basicConfig(
                level=getattr(logging, self.config.LOG_LEVEL),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

            # Setup file and console handlers
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

            file_handler = logging.FileHandler(log_dir / self.config.LOG_FILENAME)
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
        """Initialize database connection"""
        try:
            engine, db_session = self.db_config.init_db()
            self.components['db_engine'] = engine

            # Set up database on Flask app
            class DBHandle:
                def __init__(self, session, engine):
                    self.session = session
                    self.engine = engine

            self.app.db = DBHandle(db_session, engine)

            @self.app.teardown_appcontext
            def cleanup_db_session(exception=None):
                if self.db_config:
                    self.db_config.cleanup()

            self.logger.info("Database initialized successfully")
            return db_session

        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    def _setup_extensions(self):
        """Initialize Flask extensions"""
        try:
            # Setup CORS
            CORS(self.app,
                 resources={r"/api/*": {
                     "origins": self.config.CORS_SETTINGS['origins'],
                     "methods": self.config.CORS_SETTINGS['methods'],
                     "allow_headers": self.config.CORS_SETTINGS['allow_headers']
                 }},
                 supports_credentials=True)

            # Initialize JWT Manager
            self.jwt_manager = JWTTokenManager()
            self.jwt_manager.init_app(self.app)

            # Configure CORS headers
            @self.app.after_request
            def after_request(response):
                origin = request.headers.get('Origin')
                if origin:
                    # Check if origin is in allowed origins (case-insensitive)
                    allowed_origins = [o.lower() for o in self.config.CORS_SETTINGS['origins'] if o]
                    if origin.lower() in allowed_origins:
                        response.headers.update({
                            'Access-Control-Allow-Origin': origin,
                            'Access-Control-Allow-Methods': ', '.join(self.config.CORS_SETTINGS['methods']),
                            'Access-Control-Allow-Headers': ', '.join(self.config.CORS_SETTINGS['allow_headers']),
                            'Access-Control-Allow-Credentials': str(
                                self.config.CORS_SETTINGS.get('supports_credentials', True)).lower(),
                            'Access-Control-Max-Age': '3600'
                        })

                if request.method == 'OPTIONS':
                    response.status_code = 200

                return response

            self.logger.info("Extensions initialized successfully")
        except Exception as e:
            self.logger.error(f"Extension initialization failed: {e}")
            raise

    def _register_health_check(self):
        """Register health check endpoint"""
        @self.app.route("/api/v1/health")
        def health_check():
            try:
                # Check database connection
                db = getattr(self.app, 'db', None)
                if db and hasattr(db, 'session'):
                    with db.session.begin():
                        db.session.execute(text("SELECT 1"))
                    db_status = 'connected'
                else:
                    db_status = 'not configured'

                # Check component health
                component_health = {
                    name: 'healthy' for name, component in self.components.items()
                    if hasattr(component, 'is_healthy') and component.is_healthy()
                }

                return {
                    'status': 'healthy',
                    'db': db_status,
                    'environment': self.config.ENV,
                    'components': component_health
                }

            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return {
                    'status': 'unhealthy',
                    'error': str(e)
                }, 500

    def _register_routes(self) -> None:
        """Register all application routes and blueprints."""
        try:
            create_blueprints(self.app, self.services, self.jwt_manager)
            self.logger.info("Routes registered successfully")
        except Exception as e:
            self.logger.error(f"Route registration failed: {str(e)}")
            raise

    def _register_error_handlers(self) -> None:
        """Register application error handlers."""
        register_error_handlers(self.app)

    async def _init_async_resources(self):
        """Initialize async components and resources"""
        try:
            # Initialize message broker first
            message_broker = MessageBroker()
            self.components['message_broker'] = message_broker

            # Initialize core components
            staging_repository = StagingRepository(self.components.get('db_session'))
            storage_path = Path(self.config.STAGING_FOLDER)

            # Initialize StagingManager first
            staging_manager = StagingManager(
                message_broker=message_broker,
                repository=staging_repository,
                storage_path=storage_path,
                component_name="staging_manager",
                domain_type="staging"
            )
            await staging_manager.start()  # Use start() instead of _initialize_manager
            self.components['staging_manager'] = staging_manager

            # Define components to initialize
            components_to_initialize = [
                ('cpm', ControlPointManager(
                    message_broker=message_broker,
                    staging_manager=staging_manager
                )),
                ('quality_manager', QualityManager(
                    message_broker=message_broker,
                    component_name="quality_manager",
                    domain_type="quality"
                )),
                # ... other managers ...
                ('decision_manager', DecisionManager(
                    message_broker=message_broker,
                    component_name="decision_manager",
                    domain_type="decision"
                ))
            ]

            # Initialize components concurrently
            init_tasks = []
            for name, component in components_to_initialize:
                self.components[name] = component
                if hasattr(component, 'start'):  # Use start() instead of _initialize_manager
                    init_tasks.append(component.start())

            if init_tasks:
                await asyncio.gather(*init_tasks)

            # Set up component dependencies after initialization
            self.components['cpm'].staging_manager = self.components['staging_manager']

        except Exception as e:
            self.logger.error(f"Failed to initialize async resources: {e}")
            raise

    async def _cleanup_async_resources(self):
        """Cleanup async components in reverse initialization order."""
        for name, component in reversed(list(self.components.items())):
            try:
                if hasattr(component, 'cleanup') and asyncio.iscoroutinefunction(component.cleanup):
                    await component.cleanup()
            except Exception as e:
                self.logger.error(f"Failed to clean up {name}: {e}")

    def _initialize_services(self, db_session: scoped_session) -> None:
        """Initialize services with proper dependency management."""
        try:
            # Get required components
            message_broker = self.components.get('message_broker')
            if not message_broker:
                raise ValueError("Message broker not initialized")

            staging_manager = self.components.get('staging_manager')
            if not staging_manager:
                raise ValueError("Staging manager not initialized")

            cpm = self.components.get('cpm')
            if not cpm:
                raise ValueError("Control Point Manager not initialized")

            # Initialize validation configurations
            validation_configs = ValidationConfigs()

            # First add core components that other services depend on
            self.services = {
                'staging_manager': staging_manager,
                'cpm': cpm
            }

            # Initialize auth service
            auth_services = {
                'auth_service': AuthService(
                    db_session=db_session
                )
            }

            # Initialize source services
            source_services = {
                'file_service': FileService(
                    staging_manager=staging_manager,
                    cpm=cpm,
                    config={
                        'validation': validation_configs.file,
                        'staging_path': str(self.config.STAGING_FOLDER),
                        'chunk_size': 1024 * 1024  # 1MB chunks
                    }
                ),
                'db_service': DBService(
                    staging_manager=staging_manager,
                    cpm=cpm,
                    config={
                        'validation': validation_configs.database,
                        'pool_size': 5,
                        'max_overflow': 10,
                        'pool_timeout': 30
                    }
                ),
                'api_service': APIService(
                    staging_manager=staging_manager,
                    cpm=cpm,
                    config={
                        'validation': validation_configs.api,
                        'request_timeout': 30,
                        'response_cache_ttl': 300
                    }
                ),
                's3_service': S3Service(
                    staging_manager=staging_manager,
                    cpm=cpm,
                    config={
                        'validation': validation_configs.s3,
                        'bucket_name': os.getenv('S3_BUCKET_NAME'),
                        'region': os.getenv('AWS_REGION')
                    }
                ),
                'stream_service': StreamService(
                    staging_manager=staging_manager,
                    cpm=cpm,
                    config={
                        'validation': validation_configs.stream,
                        'consumer_group': 'data_pipeline',
                        'auto_offset_reset': 'earliest'
                    }
                )
            }

            # Initialize pipeline and processing services
            processing_services = {
                'pipeline_service': PipelineService(
                    message_broker=message_broker,
                ),
                'quality_service': QualityService(
                    message_broker=message_broker
                ),
                'insight_service': InsightService(
                    message_broker=message_broker
                ),
                'analytics_service': AnalyticsService(
                    message_broker=message_broker
                ),
                'recommendation_service': RecommendationService(
                    message_broker=message_broker
                ),
                'decision_service': DecisionService(
                    message_broker=message_broker
                ),
                'monitoring_service': MonitoringService(
                    message_broker=message_broker
                ),
                'report_service': ReportService(
                    message_broker=message_broker
                )
            }

            # Initialize staging service
            staging_services = {
                'staging_service': StagingService(
                    message_broker=message_broker
                )
            }

            # Update all services
            self.services.update(auth_services)
            self.services.update(source_services)
            self.services.update(processing_services)
            self.services.update(staging_services)

            # Make services available to Flask app
            self.app.services = self.services

            self.logger.info("Services initialized successfully")

        except Exception as e:
            self.logger.error(f"Service initialization failed: {str(e)}")
            raise

    async def create_app(self, config_name: str = 'development') -> Flask:
        """Create and configure Flask application"""
        try:
            async with self.lifespan_context(config_name):
                self.logger.info(f"Application initialized successfully in {config_name} mode")
                return self.app

        except Exception as e:
            self.logger.error(f"Application creation failed: {e}")
            raise
