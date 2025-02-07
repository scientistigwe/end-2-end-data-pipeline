# backend/api/app.py

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
import logging
from typing import Dict, Any, Optional
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Import configurations
from config.app_config import get_config
from config.database import DatabaseConfig

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

from config.validation_config import ValidationConfigs

# Import FastAPI routers (to be created)
from api.fastapi_app.routers import (
    analytics, auth, data_sources, decisions,
    insight, monitoring, pipeline, quality,
    recommendations, reports, staging
)

# Import middleware
from api.fastapi_app.middleware.auth_middleware import verify_token
from api.fastapi_app.middleware.error_handler import handle_exceptions

logger = logging.getLogger(__name__)


class ApplicationFactory:
    """Enhanced async application factory for FastAPI with component lifecycle management"""

    def __init__(self):
        self.app: Optional[FastAPI] = None
        self.components: Dict[str, Any] = {}
        self.services: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self.config = None
        self.db_config = None

    async def _cleanup_async_resources(self):
        """Cleanup async components in reverse initialization order."""
        for name, component in reversed(list(self.components.items())):
            try:
                if hasattr(component, 'cleanup'):
                    if asyncio.iscoroutinefunction(component.cleanup):
                        await component.cleanup()
                    else:
                        component.cleanup()
            except Exception as e:
                self.logger.error(f"Failed to clean up {name}: {e}")

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Application lifespan for managing async resources"""
        try:
            # Configure basic necessities
            self._configure_paths()
            self._configure_logging()

            # Initialize database
            await self._setup_database()

            # Initialize async resources
            await self._init_async_resources()

            # Initialize services
            await self._initialize_services()

            yield
        finally:
            await self._cleanup_async_resources()
            if self.db_config:
                await self.db_config.cleanup()

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

            logging.basicConfig(
                level=getattr(logging, self.config.LOG_LEVEL),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_dir / self.config.LOG_FILENAME),
                    logging.StreamHandler()
                ]
            )

            self.logger.info("Logging configured successfully")
        except Exception as e:
            self.logger.error(f"Logging configuration failed: {str(e)}")
            raise

    async def _setup_database(self):
        """Initialize database connection and session factory"""
        try:
            await self.db_config.init_db()
            engine = self.db_config.engine

            async_session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False
            )

            self.components['db_session'] = async_session_factory
            return async_session_factory

        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    def create_app(self, config_name: str = 'development') -> FastAPI:
        """Create and configure FastAPI application"""
        try:
            # Create FastAPI app
            self.app = FastAPI(
                title="Data Pipeline API",
                description="End-to-end data pipeline API",
                version="1.0.0",
                lifespan=self.lifespan
            )

            # Load config
            app_config = get_config(config_name)
            self.config = app_config

            # Configure CORS
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.CORS_SETTINGS['origins'],
                allow_credentials=True,
                allow_methods=self.config.CORS_SETTINGS['methods'],
                allow_headers=self.config.CORS_SETTINGS['allow_headers']
            )

            # Add exception handlers
            self.app.add_exception_handler(Exception, handle_exceptions)

            # Include routers
            self.app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
            self.app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
            self.app.include_router(data_sources.router, prefix="/api/v1/data-sources", tags=["Data Sources"])
            self.app.include_router(decisions.router, prefix="/api/v1/decisions", tags=["Decisions"])
            self.app.include_router(insight.router, prefix="/api/v1/insight", tags=["Insight"])
            self.app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["Monitoring"])
            self.app.include_router(pipeline.router, prefix="/api/v1/pipeline", tags=["Pipeline"])
            self.app.include_router(quality.router, prefix="/api/v1/quality", tags=["Quality"])
            self.app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["Recommendations"])
            self.app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
            self.app.include_router(staging.router, prefix="/api/v1/staging", tags=["Staging"])

            # Add health check endpoint
            @self.app.get("/api/v1/health", tags=["Health"])
            async def health_check():
                try:
                    # Check database connection
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

            return self.app

        except Exception as e:
            self.logger.error(f"Application creation failed: {e}")
            raise