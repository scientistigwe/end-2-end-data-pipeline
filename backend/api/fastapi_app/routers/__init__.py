from fastapi import FastAPI, APIRouter
from typing import Dict, Any, Optional
from ..auth.jwt_manager import JWTTokenManager

# Import routers
from ..routers import (
    auth,
    data_sources,
    pipeline,
    staging
)


class RouterManager:
    """Manages the creation and registration of FastAPI routers."""

    def __init__(
            self,
            app: FastAPI,
            services: Dict[str, Any],
            jwt_manager: JWTTokenManager
    ):
        self.app = app
        self.services = services
        self.jwt_manager = jwt_manager
        self.db_config = None
        self.async_session_factory = None
        self.staging_manager = None

    def _validate_core_dependencies(self) -> None:
        """Validate core application dependencies."""
        if not self.jwt_manager:
            raise ValueError("JWT manager not initialized")

        if not hasattr(self.app, 'db_config'):
            raise AttributeError("Database configuration not found")

        self.db_config = self.app.db_config

    def _setup_database(self) -> None:
        """Setup database session and configuration."""
        self.async_session_factory = self.db_config.session_factory()
        if not self.async_session_factory:
            raise ValueError("Failed to create async session factory")

        if not hasattr(self.app, 'db'):
            self.app.db = type('DB', (), {
                'async_session_factory': self.async_session_factory,
                'engine': self.db_config.engine,
                'config': self.db_config
            })

    def _validate_services(self) -> tuple[list[str], list[str]]:
        """Validate required services and their health checks."""
        service_categories = {
            'core': {
                'auth_service': 'Authentication service',
                'staging_manager': 'Staging manager'
            },
            'data_sources': {
                'file_service': 'File service',
                'db_service': 'Database service',
                's3_service': 'S3 service',
                'api_service': 'API service',
                'stream_service': 'Stream service'
            },
            'processing': {
                'pipeline_service': 'Pipeline service',
                'quality_service': 'Quality service',
                'analytics_service': 'Analytics service',
                'insight_service': 'Insight service'
            },
            'decision_making': {
                'recommendation_service': 'Recommendation service',
                'decision_service': 'Decision service'
            },
            'monitoring': {
                'monitoring_service': 'Monitoring service',
                'report_service': 'Report service',
                'staging_service': 'Staging service'
            }
        }

        missing = []
        invalid = []

        for category, services in service_categories.items():
            for service_key, service_name in services.items():
                service = self.services.get(service_key)
                if not service:
                    missing.append(f"{service_name} ({service_key})")
                elif not hasattr(service, 'is_healthy'):
                    invalid.append(f"{service_name} missing health check")

        return missing, invalid

    def _create_routers(self) -> Dict[str, APIRouter]:
        """Create application routers."""
        # Get staging_manager reference
        self.staging_manager = self.services['staging_manager']

        return {
            'auth': auth.router,
            'data-sources': data_sources.router,
            'pipeline': pipeline.router,
            'staging': staging.router
        }

    def _register_routers(self, routers: Dict[str, APIRouter]) -> None:
        """Register routers with the FastAPI application."""
        for name, router in routers.items():
            if router is None:
                raise ValueError(f"Router {name} was not properly created")

            url_prefix = f'/api/v1/{name}'
            self.app.include_router(router, prefix=url_prefix)
            self.app.logger.info(f"Registered router: {name} with prefix {url_prefix}")

    def setup(self) -> None:
        """Setup and register all routers."""
        try:
            # 1. Validate core dependencies
            self._validate_core_dependencies()

            # 2. Setup database
            self._setup_database()

            # 3. Validate services
            missing_services, invalid_services = self._validate_services()
            if missing_services:
                raise ValueError(f"Missing required services: {', '.join(missing_services)}")
            if invalid_services:
                self.app.logger.warning(f"Services with missing health checks: {', '.join(invalid_services)}")

            # 4. Create and register routers
            routers = self._create_routers()
            self._register_routers(routers)

        except Exception as e:
            self.app.logger.error(f"Failed to setup routers: {str(e)}", exc_info=True)
            raise


def setup_routers(
        app: FastAPI,
        services: Dict[str, Any],
        jwt_manager: JWTTokenManager
) -> None:
    """
    Register all application routers with their required service dependencies.

    Args:
        app: FastAPI application instance
        services: Dictionary containing service instances
        jwt_manager: JWT manager for authentication
    """
    router_manager = RouterManager(app, services, jwt_manager)
    router_manager.setup()