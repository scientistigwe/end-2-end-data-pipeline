# backend/api/app.py
from fastapi.responses import JSONResponse
from api.fastapi_app.routers.auth import register_auth_exception_handlers
from fastapi import FastAPI, Request, Depends
from contextlib import asynccontextmanager
from pathlib import Path
import logging
from typing import Dict, Any, Optional
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Import configurations
from config.app_config import get_config
from config.database import DatabaseConfig
from config.validation_config import ValidationConfigs

# Import core components
from core.messaging.broker import MessageBroker
from core.control.cpm import ControlPointManager
from core.messaging.event_types import (
    MessageType, ProcessingStage, ProcessingStatus, MessageMetadata,
    ComponentType, ModuleIdentifier
)

# Import repositories and services
from db.repository.staging import StagingRepository
from db.repository.data import DataRepository
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

# Import FastAPI routers
from .fastapi_app.routers import (
    auth,
    data_sources,
    pipeline,
    staging
)

# Import middleware
from .fastapi_app.middleware import (
    RequestLoggingMiddleware,
    ErrorHandlingMiddleware,
    setup_cors,
    get_cors_config
)

logger = logging.getLogger(__name__)


class ApplicationFactory:
    def __init__(self):
        self.app: Optional[FastAPI] = None
        self.components: Dict[str, Any] = {}
        self.services: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self.config = None
        self.db_config = None

    async def configure(self, app: FastAPI, config_name: str = 'development'):
        """
        Configure the FastAPI application with all necessary components

        Args:
            app (FastAPI): The FastAPI application instance
            config_name (str, optional): Configuration environment. Defaults to 'development'.
        """
        try:
            # Store the app reference
            self.app = app

            # Load config
            self.config = get_config(config_name)

            # Initialize database config
            self.db_config = DatabaseConfig()
            self.db_config.configure(self.config)

            # Setup initial components
            await self._setup_database()

            # Configure core components
            self._configure_middleware()
            self._configure_exception_handlers()
            self._configure_routes()
            self._configure_health_check()

            # Initialize core infrastructure
            await self._init_async_resources()
            await self._initialize_services()

            self.logger.info(f"Application configured successfully in {config_name} mode")

        except Exception as e:
            self.logger.error(f"Application configuration failed: {e}")
            raise

    async def _init_async_resources(self):
        """Initialize async resources and managers"""
        try:
            # Initialize message broker with retry mechanism
            message_broker = MessageBroker()
            retry_count = 0
            max_retries = 3

            while retry_count < max_retries:
                try:
                    await message_broker.initialize()
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        raise
                    self.logger.warning(f"Message broker connection attempt {retry_count} failed, retrying...")
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff

            self.components['message_broker'] = message_broker

            # Initialize service dependencies before services
            staging_manager = self.components.get('staging_manager')
            cpm = self.components.get('cpm')

            # Initialize data services with proper error handling
            data_services = {
                'file_service': FileService,
                'db_service': DBService,
                'api_service': APIService,
                's3_service': S3Service,
                'stream_service': StreamService
            }

            for service_name, service_class in data_services.items():
                try:
                    self.services[service_name] = service_class(
                        staging_manager=staging_manager,
                        cpm=cpm
                    )
                    self.logger.info(f"Initialized {service_name} successfully")
                except Exception as e:
                    self.logger.error(f"Failed to initialize {service_name}: {e}")
                    raise

            self.logger.info("Async resources initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize async resources: {e}")
            raise

    def _configure_middleware(self):
        """Configure application middleware"""
        try:
            # Setup CORS
            cors_config = get_cors_config()
            setup_cors(self.app, cors_config)

            # Add logging middleware
            self.app.add_middleware(RequestLoggingMiddleware)

            # Add error handling middleware
            self.app.add_middleware(ErrorHandlingMiddleware)

            self.logger.info("Middleware configured successfully")
        except Exception as e:
            self.logger.error(f"Failed to configure middleware: {e}")
            raise

    def _configure_routes(self):
        """Configure application routes"""
        try:
            # Updated router configuration to match new structure
            routers = [
                (auth.router, "/api/v1/auth", "Authentication"),
                (data_sources.router, "/api/v1/data-sources", "Data Sources"),
                (pipeline.router, "/api/v1/pipeline", "Pipeline"),
                (staging.router, "/api/v1/staging", "Staging")  # Now includes analytics, quality, insight, etc.
            ]

            for router, prefix, tag in routers:
                self.app.include_router(router, prefix=prefix, tags=[tag])

            self.logger.info("Routes configured successfully")
        except Exception as e:
            self.logger.error(f"Failed to configure routes: {e}")
            raise

    async def _initialize_services(self):
        """Initialize database-dependent services"""
        try:
            session_factory = self.components['db_session']

            async with session_factory() as session:
                # Initialize repositories
                staging_repo = StagingRepository(session)
                data_repo = DataRepository(session)

                message_broker = self.components['message_broker']

                # Initialize managers with timeout handling
                service_configs = {
                    'quality_service': QualityService,
                    'insight_service': InsightService,
                    'analytics_service': AnalyticsService,
                    'decision_service': DecisionService,
                    'monitoring_service': MonitoringService,
                    'report_service': ReportService,
                    'pipeline_service': PipelineService,
                    'recommendation_service': RecommendationService
                }

                for service_name, service_class in service_configs.items():
                    try:
                        async with asyncio.timeout(5.0):  # 5 second timeout
                            self.services[service_name] = service_class(
                                message_broker=message_broker
                            )
                            # Verify service health immediately
                            if hasattr(self.services[service_name], 'health_check'):
                                await self.services[service_name].health_check()
                        self.logger.info(f"Initialized {service_name} successfully")
                    except asyncio.TimeoutError:
                        self.logger.error(f"Timeout initializing {service_name}")
                        raise
                    except Exception as e:
                        self.logger.error(f"Failed to initialize {service_name}: {e}")
                        raise

                self.logger.info("Services initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            raise

    def _configure_health_check(self):
        """Configure health check and root endpoints"""

        @self.app.get("/", tags=["Root"])
        async def root():
            """
            Root endpoint providing basic system information
            """
            return {
                "application": "Analytix Flow API",
                "version": "1.0.0",
                "status": "running",
                "environment": self.config.ENV,
                "documentation": {
                    "swagger": "/docs",
                    "redoc": "/redoc"
                },
                "health_check": "/api/v1/health"
            }

        @self.app.get("/api/v1/health", tags=["Health"])
        async def health_check():
            try:
                async with self.components['db_session']() as session:
                    await session.execute("SELECT 1")

                return {
                    'status': 'healthy',
                    'db': 'connected',
                    'environment': self.config.ENV,
                    'components': {
                        name: 'healthy'
                        for name, component in self.components.items()
                        if hasattr(component, 'is_healthy') and component.is_healthy()
                    }
                }
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return {
                    'status': 'unhealthy',
                    'error': str(e)
                }

    def _configure_exception_handlers(self):
        """Configure global exception handlers"""
        try:
            # Register auth exception handlers
            register_auth_exception_handlers(self.app)

            # Global exception handler for uncaught exceptions
            @self.app.exception_handler(Exception)
            async def global_exception_handler(request: Request, exc: Exception):
                self.logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": True,
                        "message": "Internal server error",
                        "status_code": 500
                    }
                )

            self.logger.info("Exception handlers configured successfully")
        except Exception as e:
            self.logger.error(f"Failed to configure exception handlers: {e}")
            raise

    def create_app(self, config_name: str = 'development') -> FastAPI:
        """Create and configure FastAPI application"""
        try:
            # Create FastAPI app
            self.app = FastAPI(
                title="Analytix Flow API",
                description="End-to-end Analytix Flow API",
                version="1.0.0",
                lifespan=self.lifespan
            )

            # Load config
            self.config = get_config(config_name)

            # Initialize database config
            # Create instance first, then configure it
            self.db_config = DatabaseConfig()
            self.db_config.configure(self.config)

            # Configure components in order
            self._configure_middleware()
            self._configure_exception_handlers()
            self._configure_routes()
            self._configure_health_check()

            self.logger.info(f"Application created successfully in {config_name} mode")
            return self.app

        except Exception as e:
            self.logger.error(f"Application creation failed: {e}")
            raise

    async def _setup_database(self) -> None:
        """Initialize database connection and session factory."""
        try:
            if not self.db_config:
                raise ValueError("Database configuration not initialized")

            # Initialize the database
            await self.db_config.init_db()

            # Store session factory in components
            self.components['db_session'] = self.db_config.session_factory()

            self.logger.info("Database setup completed successfully")

        except Exception as e:
            self.logger.error(f"Database setup failed: {e}")
            raise

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Application lifespan for managing async resources"""
        try:
            # Configure basic necessities
            self._configure_paths()
            self._configure_logging()

            # Initialize database
            await self._setup_database()

            # Initialize async resources first (non-db dependent)
            await self._init_async_resources()

            # Then initialize database-dependent services
            await self._initialize_services()

            yield
        finally:
            await self._cleanup_async_resources()
            if self.db_config:
                await self.db_config.cleanup()

    def _configure_paths(self) -> None:
        """Configure application paths.

        Creates necessary directories for:
        - File uploads
        - Logs
        - Staging area
        - Temporary files
        - Cache
        """
        try:
            required_paths = {
                'uploads': self.config.UPLOAD_FOLDER,
                'logs': self.config.LOG_FOLDER,
                'staging': self.config.STAGING_FOLDER,
                'temp': self.config.TEMP_FOLDER,
                'cache': self.config.CACHE_FOLDER,
            }

            for path_name, path in required_paths.items():
                path_obj = Path(path)
                path_obj.mkdir(parents=True, exist_ok=True)
                # Ensure proper permissions
                path_obj.chmod(0o755)
                self.logger.info(f"Created {path_name} directory at: {path}")

            # Store paths in components for later use
            self.components['paths'] = required_paths
            self.logger.info("All application paths configured successfully")

        except PermissionError as e:
            self.logger.error(f"Permission denied while creating directories: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to configure paths: {e}")
            raise

    def _configure_logging(self) -> None:
        """Configure application logging.

        Sets up logging with:
        - File handler for persistent logs
        - Console handler for development
        - Proper formatting
        - Log rotation
        """
        try:
            log_dir = Path(self.config.LOG_FOLDER)
            log_file = log_dir / self.config.LOG_FILENAME

            # Create formatters for different handlers
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_formatter = logging.Formatter(
                '%(levelname)s: %(message)s'
            )

            # Create file handler with rotation
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10485760,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(self.config.LOG_LEVEL)

            # Create console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.DEBUG if self.config.DEBUG else logging.INFO)

            # Configure root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(self.config.LOG_LEVEL)

            # Remove existing handlers to avoid duplicates
            root_logger.handlers.clear()

            # Add handlers
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)

            # Store logger configuration in components
            self.components['logging'] = {
                'file_handler': file_handler,
                'console_handler': console_handler,
                'log_file': log_file
            }

            self.logger.info("Logging configured successfully")

        except Exception as e:
            print(f"Critical error configuring logging: {e}")  # Fallback to print
            raise

    async def _cleanup_async_resources(self) -> None:
        """Cleanup async components in reverse initialization order.

        Handles:
        - Graceful shutdown of services
        - Database connection cleanup
        - File handler cleanup
        - Message broker shutdown
        """
        cleanup_order = reversed([
            'message_broker',
            'db_session',
            'db_engine',
            'cpm',
            'file_service',
            'stream_service'
        ])

        for component_name in cleanup_order:
            component = self.components.get(component_name)
            if not component:
                continue

            try:
                self.logger.info(f"Cleaning up {component_name}")

                if hasattr(component, 'cleanup'):
                    if asyncio.iscoroutinefunction(component.cleanup):
                        await component.cleanup()
                    else:
                        component.cleanup()
                elif hasattr(component, 'close'):
                    if asyncio.iscoroutinefunction(component.close):
                        await component.close()
                    else:
                        component.close()
                elif hasattr(component, 'disconnect'):
                    if asyncio.iscoroutinefunction(component.disconnect):
                        await component.disconnect()
                    else:
                        component.disconnect()

                self.logger.info(f"Successfully cleaned up {component_name}")

            except Exception as e:
                self.logger.error(f"Error cleaning up {component_name}: {e}")
                # Continue cleanup even if one component fails

        # Clear components dictionary
        self.components.clear()
        self.services.clear()

        # Final logging cleanup
        logging_config = self.components.get('logging', {})
        for handler in logging_config.values():
            if isinstance(handler, logging.Handler):
                handler.close()

        self.logger.info("Cleanup of async resources completed")