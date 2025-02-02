from flask import Flask
from typing import Dict, Any
from config.database import DatabaseConfig
from api.flask_app.auth.jwt_manager import JWTTokenManager

# Import blueprint creation functions
from .auth.routes import create_auth_blueprint
from .data_sources.routes import create_data_source_blueprint
from .pipeline.routes import create_pipeline_blueprint
from .analytics.routes import create_analytics_blueprint
from .quality.routes import create_quality_blueprint
from .insight.routes import create_insight_blueprint
from .recommendations.routes import create_recommendation_blueprint
from .decisions.routes import create_decision_blueprint
from .monitoring.routes import create_monitoring_blueprint
from .reports.routes import create_reports_blueprint
from .staging.staging import create_staging_blueprint



def create_blueprints(app: Flask, services: Dict[str, Any], jwt_manager: JWTTokenManager) -> None:
    """
    Register all application blueprints with their required service dependencies.

    Args:
        app: Flask application instance
        services: Dictionary containing service instances
        jwt_manager: JWT manager for authentication

    Raises:
        ValueError: If required services are missing
        AttributeError: If database session is not configured
    """
    try:
        # Initialize JWT Manager
        if not jwt_manager:
            raise ValueError("JWT manager not initialized")

        # Validate database configuration
        if not hasattr(app, 'db') or not hasattr(app.db, 'session'):
            db_config = app.config.get('DATABASE_CONFIG')
            if not db_config:
                raise AttributeError("Database configuration not found in application config")

            engine, session = db_config.init_db()
            app.db = type('DB', (), {'session': session, 'engine': engine})

        db_session = app.db.session
        staging_manager = services.get('staging_manager')

        # Validate staging manager
        if not staging_manager:
            raise ValueError("Staging manager not found in services")

        # Required services validation
        required_services = {
            'auth_service', 'file_service', 'db_service', 's3_service',
            'api_service', 'stream_service', 'pipeline_service',
            'quality_service', 'recommendation_service', 'decision_service',
            'monitoring_service', 'report_service', 'staging_service',
            'staging_manager', 'analytics_service', 'insight_service'
        }

        missing_services = required_services - set(services.keys())
        if missing_services:
            raise ValueError(f"Missing required services: {missing_services}")

        # Blueprint creation with dependencies
        blueprints = {
            'auth': create_auth_blueprint(
                auth_service=services['auth_service'],
                db_session=db_session,
                jwt_manager=jwt_manager
            ),
            'data-sources': create_data_source_blueprint(
                file_service=services['file_service'],
                db_service=services['db_service'],
                s3_service=services['s3_service'],
                api_service=services['api_service'],
                stream_service=services['stream_service'],
                jwt_manager=jwt_manager  # Add JWT manager here
            ),
            'pipeline': create_pipeline_blueprint(
                pipeline_service=services['pipeline_service'],
                staging_manager=staging_manager,
                jwt_manager=jwt_manager
            ),
            'analytics': create_analytics_blueprint(
                quality_service=services['quality_service'],
                analytics_service=services['analytics_service'],
                staging_manager=staging_manager,
                jwt_manager=jwt_manager
            ),
            'quality': create_quality_blueprint(
                quality_service=services['quality_service'],
                staging_manager=staging_manager,
                jwt_manager=jwt_manager
            ),
            'insight': create_insight_blueprint(
                insight_service=services['insight_service'],
                staging_manager=staging_manager,
                jwt_manager=jwt_manager
            ),
            'recommendations': create_recommendation_blueprint(
                recommendation_service=services['recommendation_service'],
                staging_manager=staging_manager,
                jwt_manager=jwt_manager
            ),
            'decisions': create_decision_blueprint(
                decision_service=services['decision_service'],
                staging_manager=staging_manager,
                jwt_manager=jwt_manager
            ),
            'monitoring': create_monitoring_blueprint(
                monitoring_service=services['monitoring_service'],
                staging_manager=staging_manager,
                jwt_manager=jwt_manager
            ),
            'reports': create_reports_blueprint(
                report_service=services['report_service'],
                staging_manager=staging_manager,
                jwt_manager=jwt_manager
            ),
            'staging': create_staging_blueprint(
                staging_service=services['staging_service'],
                jwt_manager=jwt_manager
            )
        }

        # validation blueprints before registration with URL prefixes
        for name, blueprint in blueprints.items():
            if blueprint is None:
                raise ValueError(f"Blueprint {name} was not properly created")
            url_prefix = f'/api/v1/{name}'
            app.register_blueprint(blueprint, url_prefix=url_prefix)
            app.logger.info(f"Registered blueprint: {name} with prefix {url_prefix}")

    except Exception as e:
        app.logger.error(f"Failed to create blueprints: {str(e)}")
        raise

    except Exception as e:
        app.logger.error(f"Failed to create blueprints: {str(e)}")
        raise