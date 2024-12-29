# backend/backend/flask_api/app.py

from flask import Flask, g, request
from flask_cors import CORS
import logging
from typing import Dict, Any, Tuple, List
from .config.config import config_by_name
from .middleware.auth_middleware import auth_middleware
from .middleware.logging import RequestLoggingMiddleware
from .middleware.error_handler import register_error_handlers
from .auth.jwt_manager import JWTTokenManager
from .openapi.documentation import APIDocumentation
from database.config import init_db
from utils.route_registry import APIRoutes

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

    def _get_api_path(self, route_enum: APIRoutes) -> str:
        """Constructs the full API path from a route enum value."""
        base_path = route_enum.value.lstrip('/')  # Remove leading slash
        return f"/api/v1/{base_path}"

    def _get_route_pattern(self, route: APIRoutes) -> str:
        """Convert a route enum value to a Flask route pattern."""
        return route.value.replace('{', '<').replace('}', '>')

    def _get_base_prefix(self, route: APIRoutes) -> str:
        """Get the base prefix for a route (e.g., '/auth' from '/auth/login')."""
        return '/' + route.value.split('/')[1]

    def _get_blueprint_routes(self) -> List[Tuple[Any, str]]:
        """Get blueprint configurations with their routes."""
        from .blueprints.auth.routes import create_auth_blueprint
        from .blueprints.data_sources.routes import create_data_source_blueprint
        from .blueprints.pipeline.routes import create_pipeline_blueprint
        from .blueprints.analysis.routes import create_analysis_blueprint
        from .blueprints.recommendation_decision.routes import create_recommendation_blueprint

        return [
            (
                create_auth_blueprint(db_session=self.db_session),
                self._get_api_path(APIRoutes.AUTH_LOGIN).rsplit('/', 1)[0]
            ),
            (
                create_data_source_blueprint(
                    file_service=self.services['file_service'],
                    api_service=self.services['api_service'],
                    db_service=self.services['db_service'],
                    s3_service=self.services['s3_service'],
                    stream_service=self.services['stream_service'],
                    db_session=self.db_session
                ),
                self._get_api_path(APIRoutes.DATASOURCE_LIST).rsplit('/', 1)[0]
            ),
            (
                create_pipeline_blueprint(
                    self.services['pipeline_service'],
                    db_session=self.db_session
                ),
                self._get_api_path(APIRoutes.PIPELINE_LIST).rsplit('/', 1)[0]
            ),
            (
                create_analysis_blueprint(
                    self.services['pipeline_service'],
                    db_session=self.db_session
                ),
                self._get_api_path(APIRoutes.ANALYSIS_QUALITY_START).rsplit('/', 1)[0]
            ),
            (
                create_recommendation_blueprint(
                    self.services['pipeline_service'],
                    db_session=self.db_session
                ),
                self._get_api_path(APIRoutes.RECOMMENDATIONS_LIST).rsplit('/', 1)[0]
            )
        ]

    def _initialize_cors(self) -> None:
        """Initialize CORS with proper settings."""
        try:
            CORS(
                self.app,
                resources={
                    r"/api/*": {
                        "origins": ["http://localhost:5173"],
                        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                        "allow_headers": [
                            "content-type",
                            "authorization",
                            "x-requested-with",
                            "accept",
                            "origin"
                        ],
                        "expose_headers": [
                            "content-type",
                            "x-total-count",
                            "x-request-id"
                        ],
                        "supports_credentials": True,
                        "max_age": 3600
                    }
                }
            )

            @self.app.after_request
            def after_request(response):
                if request.method == 'OPTIONS':
                    response.headers.update({
                        'Access-Control-Allow-Origin': 'http://localhost:5173',
                        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                        'Access-Control-Allow-Headers': 'content-type, authorization, x-requested-with, accept, origin',
                        'Access-Control-Allow-Credentials': 'true',
                        'Access-Control-Max-Age': '3600'
                    })
                return response

            logger.info("CORS initialized successfully")

        except Exception as e:
            logger.error(f"CORS initialization error: {str(e)}", exc_info=True)
            raise

    def _initialize_database(self) -> None:
        """Initialize database connection and session management."""
        try:
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

            self.app.services = self.services
            logger.info("All services initialized successfully")

        except Exception as e:
            logger.error(f"Service initialization error: {str(e)}", exc_info=True)
            raise

    def _register_blueprints(self) -> None:
        """Register all application blueprints with their respective services."""
        try:
            blueprint_configs = self._get_blueprint_routes()
            
            for blueprint, url_prefix in blueprint_configs:
                self.app.register_blueprint(blueprint, url_prefix=url_prefix)
                logger.info(f"Registered blueprint at: {url_prefix}")

            logger.info("All blueprints registered successfully")

        except Exception as e:
            logger.error(f"Blueprint registration error: {str(e)}", exc_info=True)
            raise

    def _configure_security(self) -> None:
        """Configure security related components and middleware."""
        try:
            jwt_manager = JWTTokenManager(self.app)
            
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

            if self.app.config.get('JWT_BLACKLIST_ENABLED', False):
                @jwt_manager.token_in_blocklist_loader
                def check_if_token_revoked(jwt_header, jwt_payload):
                    jti = jwt_payload['jti']
                    return False  # Implement your blacklist check here

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

    def _register_health_check(self) -> None:
        """Register the health check endpoint."""
        @self.app.route(self._get_api_path(APIRoutes.HEALTH_CHECK))
        def health_check():
            try:
                g.db.execute('SELECT 1')
                db_status = 'connected'
            except Exception as e:
                logger.error(f"Database health check failed: {e}")
                db_status = 'disconnected'

            return {
                'status': 'healthy',
                'database': db_status,
                'environment': self.app.config['ENV']
            }

    def create_app(self, config_name: str = 'development') -> Flask:
        """Create and configure the Flask application instance."""
        try:
            self.app = Flask(__name__)
            self.app.config.from_object(config_by_name[config_name])

            # Initialize all components in order
            self._initialize_cors()
            self._initialize_database()
            self._initialize_components()
            self._initialize_services()
            self._register_blueprints()
            self._configure_security()
            self._initialize_documentation()
            self._register_health_check()

            # Register middleware
            self.app.before_request(auth_middleware())

            logger.info(f"Application initialized successfully in {config_name} mode")
            return self.app

        except Exception as e:
            logger.error(f"Failed to create application: {str(e)}", exc_info=True)
            raise

def create_app(config_name: str = 'development') -> Flask:
    """Application factory function."""
    return ApplicationFactory().create_app(config_name)