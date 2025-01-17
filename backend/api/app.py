# backend/backend/api/app.py

from flask import Flask, request
from flask_cors import CORS
import logging
import asyncio
from typing import Dict, Any
from pathlib import Path

# Import configurations
from backend.docs.analyst_pa.backend.config import get_config

# Import middleware
from .middleware.auth_middleware import auth_middleware
from .middleware.logging import RequestLoggingMiddleware
from .middleware.error_handler import register_error_handlers

# Import core components
from backend.core.messaging.broker import EnhancedMessageBroker
from backend.core.orchestration.pipeline_manager import PipelineManager
from backend.core.control.control_point_manager import ControlPointManager
from backend.core.orchestration.staging_manager import StagingManager

# Import route registry and response builder
from .utils.response_builder import ResponseBuilder

# Import services
from backend.data_pipeline.source.file.file_service import FileService
from backend.data_pipeline.source.database.db_service import DBService
from backend.data_pipeline.source.api.api_service import APIService
from backend.data_pipeline.source.cloud.s3_service import S3Service
from backend.data_pipeline.source.stream.stream_service import StreamService

# Import db repository
from backend.db.repository.pipeline_repository import PipelineRepository

logger = logging.getLogger(__name__)

class DataSourceTypes:
    FILE = 'file'
    DATABASE = 'db'
    API = 'api'
    S3 = 's3'
    STREAM = 'stream'

class ApplicationFactory:
    """Factory class for creating and configuring Flask application instances."""

    def __init__(self):
        self.app: Flask = None
        self.services: Dict[str, Any] = {}
        self.components: Dict[str, Any] = {}
        self.response_builder = ResponseBuilder()
        self.async_loop = None

    def _configure_paths(self) -> None:
        """Ensure required application paths exist."""
        try:
            required_folders = [
                self.app.config['UPLOAD_FOLDER'],
                self.app.config['LOG_FOLDER'],
                self.app.config['TEMP_FOLDER'],
                self.app.config['STAGING_FOLDER']
            ]

            for folder in required_folders:
                Path(folder).mkdir(parents=True, exist_ok=True)

            logger.info("Application paths configured")
        except Exception as e:
            logger.error(f"Path configuration error: {str(e)}")
            raise

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

            logger.info("CORS initialized")

        except Exception as e:
            logger.error(f"CORS initialization error: {str(e)}")
        raise


    def _initialize_core_components(self) -> None:
        """Initialize core application components."""
        try:
            # Create event loop for async operations
            self.async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.async_loop)

            # Enhanced Message Broker
            message_broker = EnhancedMessageBroker(
                max_workers=self.app.config.get('PIPELINE_MAX_WORKERS', 4)
            )
            self.components['message_broker'] = message_broker

            # Initialize db repository
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker, scoped_session
            engine = create_engine(self.app.config['SQLALCHEMY_DATABASE_URI'])
            session_factory = sessionmaker(bind=engine)
            db_session = scoped_session(session_factory)
            self.components['db_session'] = db_session

            # Pipeline Repository
            pipeline_repository = PipelineRepository(db_session)
            self.components['pipeline_repository'] = pipeline_repository

            # Control Point Manager
            control_point_manager = ControlPointManager(
                message_broker=message_broker
            )
            self.components['control_point_manager'] = control_point_manager

            # Staging Manager
            staging_manager = StagingManager(
                message_broker=message_broker,
                control_point_manager=control_point_manager
            )
            self.components['staging_manager'] = staging_manager

            # Pipeline Manager
            pipeline_manager = PipelineManager(
                message_broker=message_broker,
                repository=pipeline_repository,
                control_point_manager=control_point_manager,
                staging_manager=staging_manager
            )
            self.components['pipeline_manager'] = pipeline_manager

            # Asynchronously start message handlers
            self.async_loop.run_until_complete(asyncio.gather(
                control_point_manager.start_message_handlers(),
                staging_manager.start_message_handlers()
            ))

            logger.info("Core components initialized")
        except Exception as e:
            logger.error(f"Core component initialization error: {str(e)}")
            raise


    def _initialize_services(self) -> None:
        """Initialize all data source services with proper dependencies."""
        try:
            message_broker = self.components['message_broker']
            pipeline_repository = self.components['pipeline_repository']

            # Initialize File Service
            self.services['file_service'] = FileService(
                message_broker=message_broker,
                pipeline_repository=pipeline_repository,
                upload_folder=self.app.config['UPLOAD_FOLDER'],
                allowed_extensions=self.app.config['ALLOWED_EXTENSIONS'],
                max_file_size=self.app.config['MAX_CONTENT_LENGTH']
            )

            # Initialize other services
            self.services['db_service'] = DBService(
                message_broker=message_broker
            )

            self.services['api_service'] = APIService(
                message_broker=message_broker
            )

            self.services['s3_service'] = S3Service(
                message_broker=message_broker
            )

            self.services['stream_service'] = StreamService(
                message_broker=message_broker
            )

            logger.info("All services initialized")
        except Exception as e:
            logger.error(f"Service initialization error: {str(e)}")
            raise


    def _register_blueprints(self) -> None:
        """Register blueprint routes with proper middleware."""
        try:
            # Import data source routes blueprint
            from backend.api.app.blueprints.data_sources.routes import create_data_source_blueprint
            # Create and register data sources blueprint
            data_sources_bp = create_data_source_blueprint(
                file_service=self.services['file_service'],
                db_service=self.services['db_service'],
                s3_service=self.services['s3_service'],
                api_service=self.services['api_service'],
                stream_service=self.services['stream_service']
            )
            self.app.register_blueprint(
                data_sources_bp,
                url_prefix="/api/v1/data-sources"
            )

            logger.info("All blueprints registered")
        except Exception as e:
            logger.error(f"Blueprint registration error: {str(e)}")
            raise


    def _register_health_check(self) -> None:
        """Register health check endpoint."""

        @self.app.route("/api/v1/health")
        def health_check():
            try:
                # Collect health status from components
                health_status = {
                    'status': 'healthy',
                    'components': {
                        'message_broker': self.components[
                            'message_broker'].diagnose() if 'message_broker' in self.components else 'not initialized',
                        'control_point_manager': self.components[
                            'control_point_manager'].get_status() if 'control_point_manager' in self.components else 'not initialized',
                        'staging_manager': self.components[
                            'staging_manager'].get_status() if 'staging_manager' in self.components else 'not initialized',
                        'pipeline_manager': self.components[
                            'pipeline_manager'].get_pipeline_status() if 'pipeline_manager' in self.components else 'not initialized'
                    }
                }
                return self.response_builder.success(health_status)
            except Exception as e:
                logger.error(f"Health check error: {str(e)}")
                return self.response_builder.error("Health check failed", status_code=500)


    def _register_cleanup_handlers(self) -> None:
        """Register cleanup handlers for graceful shutdown."""
        try:
            @self.app.teardown_appcontext
            def cleanup_services(exception=None):
                try:
                    # Cleanup components
                    for component_name, component in self.components.items():
                        try:
                            if hasattr(component, 'cleanup'):
                                if asyncio.iscoroutinefunction(component.cleanup):
                                    # Use event loop to run async cleanup
                                    if self.async_loop:
                                        self.async_loop.run_until_complete(component.cleanup())
                                else:
                                    component.cleanup()
                        except Exception as cleanup_err:
                            logger.error(f"Error cleaning up {component_name}: {str(cleanup_err)}")

                    # Close db session
                    if 'db_session' in self.components:
                        self.components['db_session'].remove()

                except Exception as e:
                    logger.error(f"Cleanup error: {str(e)}")

            # Register signal handlers for graceful shutdown
            import signal
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}. Starting cleanup...")
                cleanup_services()
                exit(0)

            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)

            logger.info("Cleanup handlers registered")
        except Exception as e:
            logger.error(f"Error registering cleanup handlers: {str(e)}")
            raise


    def _cleanup_on_error(self) -> None:
        """Emergency cleanup if initialization fails."""
        for component_name, component in self.components.items():
            try:
                if hasattr(component, 'cleanup'):
                    # Try synchronous cleanup first
                    if not asyncio.iscoroutinefunction(component.cleanup):
                        component.cleanup()
                    elif self.async_loop:
                        # If async, use event loop
                        self.async_loop.run_until_complete(component.cleanup())
            except Exception as e:
                logger.error(f"Error cleaning up {component_name}: {str(e)}")


    def create_app(self, config_name: str = 'development') -> Flask:
        """Create and configure the Flask application."""
        try:
            # Initialize Flask app
            self.app = Flask(__name__)
            self.app.config.from_object(get_config(config_name))

            # Configure logging first
            logging.basicConfig(
                level=self.app.config.get('LOG_LEVEL', logging.INFO),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

            # Initialize in order
            self._configure_paths()
            self._initialize_cors()
            self._initialize_core_components()
            self._initialize_services()

            # Register routes and handlers
            self._register_blueprints()
            self._register_health_check()
            register_error_handlers(self.app)
            self._register_cleanup_handlers()

            # Add middleware
            self.app.wsgi_app = RequestLoggingMiddleware(self.app.wsgi_app)
            self.app.before_request(auth_middleware())

            # Store components in app context
            self.app.components = self.components
            self.app.services = self.services

            logger.info(f"Application initialized in {config_name} mode")
            return self.app

        except Exception as e:
            logger.error(f"Application creation failed: {str(e)}")
            self._cleanup_on_error()
            raise
        finally:
            # Close async loop if it exists
            if self.async_loop and not self.async_loop.is_closed():
                self.async_loop.close()


def create_app(config_name: str = 'development') -> Flask:
    """Application factory function."""
    return ApplicationFactory().create_app(config_name)


# Optional: Development server configuration
if __name__ == '__main__':
    app = create_app('development')
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )