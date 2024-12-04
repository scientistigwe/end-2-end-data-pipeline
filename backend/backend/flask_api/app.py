# app/__init__.py
from flask import Flask
from flask_cors import CORS
import logging
from typing import Dict, Any
from .config.config import config_by_name
from .middleware.logging import RequestLoggingMiddleware
from .middleware.error_handler import register_error_handlers
from .auth.jwt_manager import JWTTokenManager
from .openapi.documentation import APIDocumentation

# Import services
from .services.file_service import FileService
from .services.api_service import APIService
from .services.db_service import DBService
from .services.s3_service import S3Service
from .services.stream_service import StreamService
from .services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)


class ApplicationFactory:
    def __init__(self):
        self.app = None
        self.services: Dict[str, Any] = {}
        self.components = None

    def create_app(self, config_name: str = 'development') -> Flask:
        try:
            # Initialize Flask
            self.app = Flask(__name__)
            self.app.config.from_object(config_by_name[config_name])

            # Initialize components and middleware
            self._initialize_components()
            self._initialize_middleware()
            self._initialize_services()
            self._register_blueprints()
            self._configure_security()
            self._initialize_documentation()

            logger.info(f"Application initialized successfully in {config_name} mode")
            return self.app
        except Exception as e:
            logger.error(f"Failed to create application: {str(e)}", exc_info=True)
            raise

    def _initialize_services(self):
        """Initialize all application services"""
        try:
            # Initialize core services
            self.services['file_service'] = FileService(
                message_broker=self.components['message_broker'],
                orchestrator=self.components['orchestrator']
            )

            self.services['api_service'] = APIService(
                message_broker=self.components['message_broker'],
                orchestrator=self.components['orchestrator']
            )

            self.services['db_service'] = DBService(
                message_broker=self.components['message_broker'],
                orchestrator=self.components['orchestrator']
            )

            self.services['s3_service'] = S3Service(
                message_broker=self.components['message_broker'],
                orchestrator=self.components['orchestrator']
            )

            self.services['stream_service'] = StreamService(
                message_broker=self.components['message_broker'],
                orchestrator=self.components['orchestrator']
            )

            self.services['pipeline_service'] = PipelineService(
                orchestrator=self.components['orchestrator'],
                message_broker=self.components['message_broker']
            )

            # Attach services to app context
            self.app.services = self.services
            logger.info("All services initialized successfully")

        except Exception as e:
            logger.error(f"Service initialization error: {str(e)}", exc_info=True)
            raise

    def _register_blueprints(self):
        """Register all application blueprints with their respective services"""
        try:
            # Import blueprints
            from .blueprints.auth.routes import create_auth_blueprint
            from .blueprints.data_sources.routes import create_data_source_blueprint
            from .blueprints.pipeline.routes import create_pipeline_blueprint
            from .blueprints.analysis.routes import create_analysis_blueprint
            from .blueprints.recommendations.routes import create_recommendation_blueprint

            # Register blueprints with services
            self.app.register_blueprint(
                create_auth_blueprint(),
                url_prefix='/api/v1/auth'
            )

            self.app.register_blueprint(
                create_data_source_blueprint(
                    file_service=self.services['file_service'],
                    api_service=self.services['api_service'],
                    db_service=self.services['db_service'],
                    s3_service=self.services['s3_service'],
                    stream_service=self.services['stream_service']
                ),
                url_prefix='/api/v1/data-sources'
            )

            self.app.register_blueprint(
                create_pipeline_blueprint(self.services['pipeline_service']),
                url_prefix='/api/v1/pipeline'
            )

            self.app.register_blueprint(
                create_analysis_blueprint(self.services['pipeline_service']),
                url_prefix='/api/v1/analysis'
            )

            self.app.register_blueprint(
                create_recommendation_blueprint(self.services['pipeline_service']),
                url_prefix='/api/v1/recommendations'
            )

            logger.info("All blueprints registered successfully")

        except Exception as e:
            logger.error(f"Blueprint registration error: {str(e)}", exc_info=True)
            raise


def create_app(config_name: str = 'development') -> Flask:
    """Application factory function"""
    return ApplicationFactory().create_app(config_name)