# Import blueprint creation functions
from backend.api.fastapi_app.routers.auth import create_auth_blueprint
from backend.api.fastapi_app.routers.data_sources import create_data_source_blueprint
from backend.api.fastapi_app.routers.pipeline import create_pipeline_blueprint
from backend.api.fastapi_app.routers.analytics import create_analytics_blueprint
from backend.api.fastapi_app.routers.quality import create_quality_blueprint
from backend.api.fastapi_app.routers.insight import create_insight_blueprint
from backend.api.fastapi_app.routers.recommendations import create_recommendation_blueprint
from backend.api.fastapi_app.routers.decisions import create_decision_blueprint
from backend.api.fastapi_app.routers.monitoring import create_monitoring_blueprint
from backend.api.fastapi_app.routers.reports import create_reports_blueprint
from backend.api.fastapi_app.routers.staging import create_staging_blueprint

from flask import Flask
from typing import Dict, Any, List, Tuple
from api.flask_app.auth.jwt_manager import JWTTokenManager


class BlueprintManager:
    """Manages the creation and registration of Flask routers."""

    def __init__(self, app: Flask, services: Dict[str, Any], jwt_manager: JWTTokenManager):
        self.app = app
        self.services = services
        self.jwt_manager = jwt_manager
        self.db_config = None
        self.async_session_factory = None
        self.staging_manager = None

    def _validate_core_dependencies(self):
        """Validate core application dependencies."""
        if not self.jwt_manager:
            raise ValueError("JWT manager not initialized")

        self.db_config = self.app.config.get('DATABASE_CONFIG')
        if not self.db_config:
            raise AttributeError("Database configuration not found")

    def _setup_database(self):
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

    def _validate_services(self) -> Tuple[List[str], List[str]]:
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

    def _create_blueprints(self) -> Dict[str, Any]:
        """Create application routers."""
        # Get staging_manager reference
        self.staging_manager = self.services['staging_manager']

        return {
            'auth': create_auth_blueprint(
                auth_service=self.services['auth_service'],
                jwt_manager=self.jwt_manager
            ),
            'data-sources': create_data_source_blueprint(
                file_service=self.services['file_service'],
                db_service=self.services['db_service'],
                s3_service=self.services['s3_service'],
                api_service=self.services['api_service'],
                stream_service=self.services['stream_service'],
                jwt_manager=self.jwt_manager
            ),
            'pipeline': create_pipeline_blueprint(
                pipeline_service=self.services['pipeline_service'],
                staging_manager=self.staging_manager,
                jwt_manager=self.jwt_manager
            ),
            'analytics': create_analytics_blueprint(
                quality_service=self.services['quality_service'],
                analytics_service=self.services['analytics_service'],
                staging_manager=self.staging_manager,
                jwt_manager=self.jwt_manager
            ),
            'quality': create_quality_blueprint(
                quality_service=self.services['quality_service'],
                staging_manager=self.staging_manager,
                jwt_manager=self.jwt_manager
            ),
            'insight': create_insight_blueprint(
                insight_service=self.services['insight_service'],
                staging_manager=self.staging_manager,
                jwt_manager=self.jwt_manager
            ),
            'recommendations': create_recommendation_blueprint(
                recommendation_service=self.services['recommendation_service'],
                staging_manager=self.staging_manager,
                jwt_manager=self.jwt_manager
            ),
            'decisions': create_decision_blueprint(
                decision_service=self.services['decision_service'],
                staging_manager=self.staging_manager,
                jwt_manager=self.jwt_manager
            ),
            'monitoring': create_monitoring_blueprint(
                monitoring_service=self.services['monitoring_service'],
                staging_manager=self.staging_manager,
                jwt_manager=self.jwt_manager
            ),
            'reports': create_reports_blueprint(
                report_service=self.services['report_service'],
                staging_manager=self.staging_manager,
                jwt_manager=self.jwt_manager
            ),
            'staging': create_staging_blueprint(
                staging_service=self.services['staging_service'],
                jwt_manager=self.jwt_manager
            )
        }

    def _register_blueprints(self, blueprints: Dict[str, Any]):
        """Register routers with the Flask application."""
        for name, blueprint in blueprints.items():
            if blueprint is None:
                raise ValueError(f"Blueprint {name} was not properly created")
            url_prefix = f'/api/v1/{name}'
            self.app.register_blueprint(blueprint, url_prefix=url_prefix)
            self.app.logger.info(f"Registered blueprint: {name} with prefix {url_prefix}")

    def setup(self):
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
            blueprints = self._create_blueprints()
            self._register_blueprints(blueprints)

        except Exception as e:
            self.app.logger.error(f"Failed to create routers: {str(e)}", exc_info=True)
            raise


def create_blueprints(app: Flask, services: Dict[str, Any], jwt_manager: JWTTokenManager) -> None:
    """
    Register all application routers with their required service dependencies.

    Args:
        app: Flask application instance
        services: Dictionary containing service instances
        jwt_manager: JWT manager for authentication
    """
    blueprint_manager = BlueprintManager(app, services, jwt_manager)
    blueprint_manager.setup()



