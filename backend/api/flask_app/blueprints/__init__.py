from flask import Flask
from typing import Dict, Any
from config.database import DatabaseConfig

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
from .settings.routes import create_settings_blueprint
from .staging.staging import create_staging_blueprint


def create_blueprints(app: Flask, services: Dict[str, Any]) -> None:
    """
    Register all application blueprints with their required service dependencies.

    This function validates service availability and sets up blueprints with
    appropriate dependencies and URL prefixes. It uses the database session
    provided by the application's database configuration.

    Args:
        app: Flask application instance
        services: Dictionary containing service instances

    Raises:
        ValueError: If required services are missing
        AttributeError: If database session is not configured
    """
    try:
        # Use the application's existing database configuration
        if not hasattr(app, 'db') or not hasattr(app.db, 'session'):
            db_config = app.config.get('DATABASE_CONFIG')
            if not db_config:
                raise AttributeError("Database configuration not found in application config")

            engine, session = db_config.init_db()
            app.db = type('DB', (), {'session': session, 'engine': engine})

        db_session = app.db.session
        staging_manager = services.get('staging_manager')

        if not staging_manager:
            raise ValueError("Staging manager not found in services")

        # Required services validation
        required_services = {
            'auth_service', 'file_service', 'db_service', 's3_service',
            'api_service', 'stream_service', 'pipeline_service',
            'quality_service', 'recommendation_service', 'decision_service',
            'monitoring_service', 'report_service', 'settings_service',
            'staging_service', 'staging_manager', 'analytics_service', 'insight_service'
        }

        missing_services = required_services - set(services.keys())
        if missing_services:
            raise ValueError(f"Missing required services: {missing_services}")

        # Blueprint creation with dependencies
        blueprints = {
            'auth': create_auth_blueprint(
                services['auth_service'],
                db_session
            ),
            'data_sources': create_data_source_blueprint(
                file_service=services['file_service'],
                db_service=services['db_service'],
                s3_service=services['s3_service'],
                api_service=services['api_service'],
                stream_service=services['stream_service']
            ),
            'pipeline': create_pipeline_blueprint(
                pipeline_service=services['pipeline_service'],
                staging_manager=staging_manager
            ),
            'analytics': create_analytics_blueprint(
                services['analytics_service']
            ),
            'quality': create_quality_blueprint(
                services['quality_service']
            ),
            'insight': create_insight_blueprint(
                services['insight_service']
            ),
            'recommendations': create_recommendation_blueprint(
                services['recommendation_service']
            ),
            'decisions': create_decision_blueprint(
                services['decision_service']
            ),
            'monitoring': create_monitoring_blueprint(
                services['monitoring_service']
            ),
            'reports': create_reports_blueprint(
                services['report_service']
            ),
            'settings': create_settings_blueprint(
                services['settings_service']
            ),
            'staging': create_staging_blueprint(
                services['staging_service']
            )
        }

        # Register blueprints with URL prefixes
        for name, blueprint in blueprints.items():
            url_prefix = f'/api/v1/{name}'
            app.register_blueprint(blueprint, url_prefix=url_prefix)
            app.logger.info(f"Registered blueprint: {name}")

    except Exception as e:
        app.logger.error(f"Failed to create blueprints: {str(e)}")
        raise