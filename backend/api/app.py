# backend/app.py

from flask import Flask
from flask_cors import CORS
import logging
import asyncio
from pathlib import Path

# Import configurations
from backend.config import get_config, init_db, cleanup_db

# Import middleware
from backend.api.app.middleware.auth_middleware import auth_middleware
from backend.api.app.middleware.logging import RequestLoggingMiddleware
from backend.api.app.middleware.error_handler import register_error_handlers

# Import core components
from backend.core.messaging.broker import MessageBroker
from backend.core.control.cpm import ControlPointManager
from backend.core.staging.staging_manager import StagingManager

# Import db repository
from backend.db.repository.staging_repository import StagingRepository

# Import services
from backend.data.source.file.file_service import FileService
from backend.data.source.database import DBService
from backend.data.source.api import APIService
from backend.data.source.cloud.cloud_service import S3Service
from backend.data.source.stream.stream_service import StreamService

logger = logging.getLogger(__name__)

class DataSourceTypes:
    FILE = 'file'
    DATABASE = 'db'
    API = 'api'
    S3 = 's3'
    STREAM = 'stream'


class ApplicationFactory:
    def __init__(self):
        self.app: Flask = None
        self.async_loop = None
        self._init_async_loop()

    def _init_async_loop(self):
        """Initialize async loop for async operations"""
        try:
            self.async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.async_loop)
        except Exception as e:
            logger.error(f"Failed to initialize async loop: {str(e)}")
            raise

    def _configure_paths(self) -> None:
        """Configure application paths"""
        try:
            paths = [
                self.app.config['UPLOAD_FOLDER'],
                self.app.config['LOG_FOLDER'],
                self.app.config['STAGING_FOLDER']
            ]
            for path in paths:
                Path(path).mkdir(parents=True, exist_ok=True)
            logger.info("Application paths configured successfully")
        except Exception as e:
            logger.error(f"Path configuration failed: {str(e)}")
            raise

    async def _init_core_components(self) -> None:
        """Initialize core application components"""
        try:
            # Initialize database
            engine, session = init_db(self.app)
            self.app.db_engine = engine
            self.app.db_session = session

            # Initialize repositories
            staging_repo = StagingRepository(session)
            self.app.staging_repository = staging_repo

            # Initialize message broker
            message_broker = MessageBroker()
            self.app.message_broker = message_broker

            # Initialize CPM with dependencies
            cpm = ControlPointManager(
                message_broker=message_broker,
                staging_repository=staging_repo
            )
            self.app.cpm = cpm

            # Initialize staging manager
            staging_manager = StagingManager(
                message_broker=message_broker,
                staging_repository=staging_repo,
                control_point_manager=cpm
            )
            self.app.staging_manager = staging_manager

            # Start async components
            await asyncio.gather(
                cpm.initialize(),
                staging_manager.initialize()
            )

            logger.info("Core components initialized successfully")

        except Exception as e:
            logger.error(f"Core component initialization failed: {str(e)}")
            raise

    async def _cleanup_components(self) -> None:
        """Cleanup application components"""
        try:
            if hasattr(self.app, 'staging_manager'):
                await self.app.staging_manager.cleanup()
            if hasattr(self.app, 'cpm'):
                await self.app.cpm.cleanup()
            if hasattr(self.app, 'message_broker'):
                await self.app.message_broker.cleanup()
            if hasattr(self.app, 'db_engine'):
                cleanup_db(self.app.db_engine)

            logger.info("Components cleaned up successfully")
        except Exception as e:
            logger.error(f"Component cleanup failed: {str(e)}")
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