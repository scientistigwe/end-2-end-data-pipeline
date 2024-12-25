# backend/backend/flask_api/app.py

from flask import Flask, g, request
from flask_cors import CORS
import logging
from typing import Dict, Any
from .config.config import config_by_name
from .middleware.logging import RequestLoggingMiddleware
from .middleware.error_handler import register_error_handlers
from .auth.jwt_manager import JWTTokenManager
from .openapi.documentation import APIDocumentation
from database.config import init_db

# Import services
from .services.file_service import FileService
from .services.api_service import APIService
from .services.db_service import DBService
from .services.s3_service import S3Service
from .services.stream_service import StreamService
from .services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)

class ApplicationFactory:
    """Factory class for creating and configuring Flask application instances."""
    
    def __init__(self):
        self.app: Flask = None
        self.services: Dict[str, Any] = {}
        self.components: Dict[str, Any] = {}
        self.db_session = None

    def _initialize_cors(self) -> None:
        """Initialize CORS with proper settings."""
        try:
            CORS(
                self.app,
                resources={
                    r"/api/*": {
                        "origins": ["http://localhost:5173"],
                        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                        "allow_headers": ["content-type, authorization, x-requested-with, accept, origin, X-Request-Time"],  
                        "expose_headers": ["content-type, x-total-count, x-request-id"],
                        "supports_credentials": True,
                        "max_age": 3600
                    }
                }
            )

            @self.app.after_request
            def after_request(response):
                if request.method == 'OPTIONS':
                    # Handle preflight
                    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:5173'
                    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                    response.headers['Access-Control-Allow-Headers'] = 'content-type, authorization, x-requested-with, accept, origin, X-Request-Time'
                    response.headers['Access-Control-Allow-Credentials'] = 'true'
                    response.headers['Access-Control-Max-Age'] = '3600'
                return response

            logger.info("CORS initialized successfully")

        except Exception as e:
            logger.error(f"CORS initialization error: {str(e)}", exc_info=True)
            raise
        
    def _initialize_database(self) -> None:
        """Initialize database connection and session management."""
        try:
            # Initialize database
            engine, SessionLocal = init_db(self.app)
            self.db_session = SessionLocal

            @self.app.before_request
            def before_request():
                """Create database session for each request."""
                g.db = self.db_session()

            @self.app.teardown_appcontext
            def teardown_db(exc):
                """Close database session after each request."""
                db = g.pop('db', None)
                if db is not None:
                    db.close()

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}", exc_info=True)
            raise

    def _initialize_components(self) -> None:
        """Initialize application components."""
        try:
            # Initialize your components here
            pass
            logger.info("Components initialized successfully")

        except Exception as e:
            logger.error(f"Component initialization error: {str(e)}", exc_info=True)
            raise

    def _initialize_services(self) -> None:
        """Initialize all application services with dependencies."""
        try:
            service_configs = {
                'file_service': FileService,
                'api_service': APIService,
                'db_service': DBService,
                's3_service': S3Service,
                'stream_service': StreamService,
                'pipeline_service': PipelineService
            }

            for service_name, ServiceClass in service_configs.items():
                self.services[service_name] = ServiceClass(
                    message_broker=self.components.get('message_broker'),
                    orchestrator=self.components.get('orchestrator'),
                    db_session=self.db_session
                )

            # Attach services to app context
            self.app.services = self.services
            logger.info("All services initialized successfully")

        except Exception as e:
            logger.error(f"Service initialization error: {str(e)}", exc_info=True)
            raise

    def _register_blueprints(self) -> None:
        """Register all application blueprints with their respective services."""
        try:
            # Import blueprints
            from .blueprints.auth.routes import create_auth_blueprint
            from .blueprints.data_sources.routes import create_data_source_blueprint
            from .blueprints.pipeline.routes import create_pipeline_blueprint
            from .blueprints.analysis.routes import create_analysis_blueprint
            from .blueprints.recommendation_decision.routes import create_recommendation_blueprint

            # Register blueprints with dependencies
            blueprints = [
                (create_auth_blueprint(db_session=self.db_session), '/api/v1/auth'),
                (create_data_source_blueprint(
                    file_service=self.services['file_service'],
                    api_service=self.services['api_service'],
                    db_service=self.services['db_service'],
                    s3_service=self.services['s3_service'],
                    stream_service=self.services['stream_service'],
                    db_session=self.db_session
                ), '/api/v1/data-sources'),
                (create_pipeline_blueprint(
                    self.services['pipeline_service'],
                    db_session=self.db_session
                ), '/api/v1/pipeline'),
                (create_analysis_blueprint(
                    self.services['pipeline_service'],
                    db_session=self.db_session
                ), '/api/v1/analysis'),
                (create_recommendation_blueprint(
                    self.services['pipeline_service'],
                    db_session=self.db_session
                ), '/api/v1/recommendations')
            ]

            # Register all blueprints
            for blueprint, url_prefix in blueprints:
                self.app.register_blueprint(blueprint, url_prefix=url_prefix)

            logger.info("All blueprints registered successfully")

        except Exception as e:
            logger.error(f"Blueprint registration error: {str(e)}", exc_info=True)
            raise

    def _configure_security(self) -> None:
        """Configure security related components and middleware."""
        try:
            # Initialize JWT manager
            jwt_manager = JWTTokenManager(self.app)
            
            # Add JWT error handlers
            @jwt_manager.expired_token_loader
            def expired_token_callback(jwt_header, jwt_payload):
                return {
                    'message': 'Token has expired',
                    'error': 'token_expired'
                }, 401

            @jwt_manager.invalid_token_loader
            def invalid_token_callback(error):
                return {
                    'message': 'Invalid token',
                    'error': 'invalid_token'
                }, 401

            @jwt_manager.unauthorized_loader
            def missing_token_callback(error):
                return {
                    'message': 'Missing authorization token',
                    'error': 'authorization_required'
                }, 401

            # Configure JWT blacklist if enabled
            if self.app.config.get('JWT_BLACKLIST_ENABLED', False):
                @jwt_manager.token_in_blocklist_loader
                def check_if_token_revoked(jwt_header, jwt_payload):
                    jti = jwt_payload['jti']
                    # Implement your token blacklist check here
                    # Example: return is_token_blacklisted(jti)
                    return False

            logger.info("Security configuration completed successfully")

        except Exception as e:
            logger.error(f"Security configuration error: {str(e)}", exc_info=True)
            raise

    def _initialize_documentation(self) -> None:
        """Initialize API documentation."""
        try:
            APIDocumentation(self.app)
            logger.info("API documentation initialized successfully")

        except Exception as e:
            logger.error(f"Documentation initialization error: {str(e)}", exc_info=True)
            raise

    def create_app(self, config_name: str = 'development') -> Flask:
        """Create and configure the Flask application instance."""
        try:
            # Initialize Flask
            self.app = Flask(__name__)
            self.app.config.from_object(config_by_name[config_name])

            # Initialize all components
            self._initialize_cors()  # Initialize CORS first
            self._initialize_database()
            self._initialize_components()
            self._initialize_services()
            self._register_blueprints()
            self._configure_security()
            self._initialize_documentation()

            # Add health check endpoint
            @self.app.route('/api/v1/health')
            def health_check():
                """Health check endpoint to verify application status."""
                try:
                    # Test database connection
                    g.db.execute('SELECT 1')
                    db_status = 'connected'
                except Exception as e:
                    logger.error(f"Database health check failed: {e}")
                    db_status = 'disconnected'

                return {
                    'status': 'healthy',
                    'database': db_status,
                    'environment': config_name
                }

            logger.info(f"Application initialized successfully in {config_name} mode")
            return self.app

        except Exception as e:
            logger.error(f"Failed to create application: {str(e)}", exc_info=True)
            raise

def create_app(config_name: str = 'development') -> Flask:
    """Application factory function."""
    return ApplicationFactory().create_app(config_name)