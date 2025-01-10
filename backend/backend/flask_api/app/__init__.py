# flask_api/app/__init__.py

from flask import Flask, g, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from functools import wraps

# Import configurations
from backend.config import get_config, init_db, cleanup_db

# Import middleware
from .middleware.error_handler import register_error_handlers
from .middleware.logging import RequestLoggingMiddleware
from .middleware.auth_middleware import auth_middleware

# Import auth manager
from .auth.jwt_manager import JWTTokenManager

# Import all services
from .services.auth.auth_service import AuthService
from .services.data_sources.file_source_service import FileSourceService
from .services.data_sources.api_service import APISourceService
from .services.data_sources.database_service import DatabaseSourceService
from .services.data_sources.s3_service import S3SourceService
from .services.data_sources.stream_service import StreamSourceService
from .services.pipeline.pipeline_service import PipelineService
from .services.analysis.quality_service import QualityService
from .services.analysis.insight_service import InsightService
from .services.decision_recommendation.recommendations_service import RecommendationService
from .services.decision_recommendation.decision_service import DecisionService
from .services.monitoring.monitoring_service import MonitoringService
from .services.reports.report_service import ReportService
from .services.settings.settings_service import SettingsService
from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.pipeline_manager import PipelineManager

logger = logging.getLogger(__name__)

# Initialize SQLAlchemy instance
db = SQLAlchemy()


def configure_logging(app: Flask) -> None:
    """Configure application logging with proper handler configuration."""
    try:
        log_dir = Path(app.config['LOG_FOLDER'])
        log_dir.mkdir(parents=True, exist_ok=True)

        # Remove all existing handlers to avoid duplicates
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        # Configure root logger at WARNING level
        logging.basicConfig(level=logging.WARNING)

        # Create formatters
        standard_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Create and configure file handler
        file_handler = logging.FileHandler(log_dir / app.config['LOG_FILENAME'])
        file_handler.setFormatter(standard_formatter)
        file_handler.setLevel(logging.INFO)

        # Create and configure console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(standard_formatter)
        console_handler.setLevel(logging.INFO)

        # Configure backend logger specifically
        backend_logger = logging.getLogger('backend')
        backend_logger.setLevel(logging.INFO)
        backend_logger.propagate = False  # Prevent duplicate logs
        backend_logger.addHandler(file_handler)
        backend_logger.addHandler(console_handler)

        # Configure SQLAlchemy logger
        sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
        sqlalchemy_logger.setLevel(logging.WARNING)  # Only show warnings and errors
        sqlalchemy_logger.propagate = False  # Prevent duplicate logs
        sqlalchemy_logger.addHandler(file_handler)
        sqlalchemy_logger.addHandler(console_handler)

        logger.info("Logging configured successfully")
    except Exception as e:
        print(f"Error configuring logging: {str(e)}")
        raise

def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions"""
    try:
        CORS(app, resources={r"/api/*": app.config['CORS_SETTINGS']})

        @app.after_request
        def after_request(response):
            if request.method == 'OPTIONS':
                response.status_code = 200
                headers = {
                    'Access-Control-Allow-Origin': app.config['CORS_SETTINGS']['origins'][0],
                    'Access-Control-Allow-Credentials': str(
                        app.config['CORS_SETTINGS']['supports_credentials']).lower(),
                    'Access-Control-Allow-Methods': ', '.join(app.config['CORS_SETTINGS']['methods']),
                    'Access-Control-Allow-Headers': ', '.join(app.config['CORS_SETTINGS']['allow_headers']),
                    'Access-Control-Max-Age': '3600'
                }
                response.headers.update(headers)
            return response

        logger.info("CORS initialized successfully")

    except Exception as e:
        logger.error(f"Extension initialization error: {str(e)}", exc_info=True)
        raise

def _init_jwt(app: Flask) -> None:
    """Initialize JWT manager with error handlers."""
    try:
        jwt = JWTManager(app)

        @jwt.unauthorized_loader
        def unauthorized_callback(error):
            return jsonify({
                'message': 'Missing authorization token',
                'error': 'authorization_required'
            }), 401

        @jwt.invalid_token_loader
        def invalid_token_callback(error):
            return jsonify({
                'message': 'Invalid token',
                'error': 'invalid_token'
            }), 401

        @jwt.expired_token_loader
        def expired_token_callback(_jwt_header, _jwt_data):
            return jsonify({
                'message': 'Token has expired',
                'error': 'token_expired'
            }), 401

        @jwt.needs_fresh_token_loader
        def token_not_fresh_callback(_jwt_header, _jwt_data):
            return jsonify({
                'message': 'Fresh token required',
                'error': 'fresh_token_required'
            }), 401

        logger.info("JWT initialized successfully")
    except Exception as e:
        logger.error(f"JWT initialization error: {str(e)}", exc_info=True)
        raise

def _init_database(app: Flask) -> Tuple[Any, Any]:
    """Initialize database connection and session management."""
    try:
        logger.info("Starting database initialization...")

        # Initialize database using the new init_db function
        engine, SessionLocal = init_db(app)

        # Set up request handlers
        @app.before_request
        def before_request():
            g.db = SessionLocal()

        @app.teardown_appcontext
        def teardown_db(exc):
            db = g.pop('db', None)
            if db is not None:
                db.close()

        logger.info("Database initialized successfully")
        return engine, SessionLocal

    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}", exc_info=True)
        raise

def _configure_paths(app: Flask) -> None:
    """Configure application paths."""
    try:
        for folder in ['UPLOAD_FOLDER', 'LOG_FOLDER']:
            directory = Path(app.config[folder])
            directory.mkdir(parents=True, exist_ok=True)

        logger.info("Application paths configured successfully")

    except Exception as e:
        logger.error(f"Path configuration error: {str(e)}", exc_info=True)
        raise

def register_blueprints(app: Flask, db_session) -> None:
    """Register all application blueprints with JWT protection."""
    try:
        from backend.flask_api.app.blueprints.auth.routes import create_auth_blueprint
        from backend.flask_api.app.blueprints.data_sources.routes import create_data_source_blueprint
        from backend.flask_api.app.blueprints.pipeline.routes import create_pipeline_blueprint
        from backend.flask_api.app.blueprints.analysis.routes import create_analysis_blueprint
        from backend.flask_api.app.blueprints.recommendations.routes import create_recommendation_blueprint
        from backend.flask_api.app.blueprints.decisions.routes import create_decision_blueprint
        from backend.flask_api.app.blueprints.monitoring.routes import create_monitoring_blueprint
        from backend.flask_api.app.blueprints.reports.routes import create_reports_blueprint
        from backend.flask_api.app.blueprints.settings.routes import create_settings_blueprint
        from flask_jwt_extended import jwt_required

        # Define blueprints with URLs from config
        public_blueprints = [
            (create_auth_blueprint(
                auth_service=app.services['auth_service'],
                db_session=db_session
            ), f"/api/{app.config['API_VERSION']}{app.config['SERVICES']['auth']}"),
        ]

        protected_blueprints = [
            (create_data_source_blueprint(
                file_service=app.services['file_service'],
                db_service=app.services['db_service'],
                s3_service=app.services['s3_service'],
                api_service=app.services['api_service'],
                stream_service=app.services['stream_service'],
                db_session=db_session
            ), f"/api/{app.config['API_VERSION']}{app.config['SERVICES']['data-sources']}"),
            (create_pipeline_blueprint(
                pipeline_service=app.services['pipeline_service'],
                db_session=db_session
            ), f"/api/{app.config['API_VERSION']}{app.config['SERVICES']['pipeline']}"),
            # ... [remaining blueprint registrations] ...
        ]

        # Register blueprints
        with app.app_context():
            # Register public blueprints
            for blueprint, url_prefix in public_blueprints:
                app.register_blueprint(blueprint, url_prefix=url_prefix)
                logger.info(f"Registered public blueprint at {url_prefix}")

            # Register protected blueprints
            for blueprint, url_prefix in protected_blueprints:
                for view_function in blueprint.view_functions.values():
                    if not hasattr(view_function, '_jwt_required'):
                        protected_view = jwt_required()(view_function)
                        protected_view._jwt_required = True
                        blueprint.view_functions[view_function.__name__] = protected_view

                app.register_blueprint(blueprint, url_prefix=url_prefix)
                logger.info(f"Registered protected blueprint at {url_prefix}")

        logger.info("All blueprints registered successfully")

    except Exception as e:
        logger.error(f"Error registering blueprints: {str(e)}", exc_info=True)
        raise

def _initialize_services(app: Flask, db_session) -> None:
    """Initialize all application services."""
    try:
        # Initialize MessageBroker first with thread pool settings
        message_broker = MessageBroker(max_workers=app.config.get('PIPELINE_MAX_WORKERS', 4))

        # Initialize PipelineManager with only required parameters
        pipeline_manager = PipelineManager(
            message_broker=message_broker,
            db_session=db_session
        )

        app.services = {
            'auth_service': AuthService(db_session),
            'file_service': FileSourceService(
                db_session,
                allowed_extensions=app.config['ALLOWED_EXTENSIONS'],
                max_file_size=app.config['MAX_CONTENT_LENGTH']
            ),
            'db_service': DatabaseSourceService(db_session),
            's3_service': S3SourceService(db_session),
            'api_service': APISourceService(db_session),
            'stream_service': StreamSourceService(db_session),
            'pipeline_service': PipelineService(
                db_session=db_session,
                message_broker=message_broker
            ),
            'quality_service': QualityService(db_session),
            'insight_service': InsightService(db_session),
            'recommendation_service': RecommendationService(db_session),
            'decision_service': DecisionService(db_session),
            'monitoring_service': MonitoringService(db_session),
            'report_service': ReportService(db_session),
            'settings_service': SettingsService(db_session)
        }

        # Store message_broker and pipeline_manager in app context
        app.message_broker = message_broker
        app.pipeline_manager = pipeline_manager

        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Service initialization error: {str(e)}", exc_info=True)
        raise

def create_app(config_name: str = 'development') -> Flask:
    """Application factory function."""
    try:
        # Initialize Flask app
        app = Flask(__name__)

        # Load configuration
        app_config = get_config(config_name)
        app.config.from_object(app_config)

        # Configure logging first
        configure_logging(app)

        # Initialize components in order
        _configure_paths(app)
        _init_extensions(app)
        _init_jwt(app)

        # Initialize database and get session
        engine, SessionLocal = _init_database(app)
        db_session = SessionLocal()

        # Initialize all services
        with app.app_context():
            _initialize_services(app, db_session)

        # Register error handlers and blueprints
        register_error_handlers(app)
        with app.app_context():
            register_blueprints(app, db_session)

        # Add request logging middleware
        app.wsgi_app = RequestLoggingMiddleware(app.wsgi_app)

        # Add auth middleware
        app.before_request(auth_middleware())

        # Add cleanup on app context teardown
        @app.teardown_appcontext
        def cleanup_services(exception=None):
            if hasattr(app, 'message_broker'):
                app.message_broker.thread_pool.shutdown(wait=True)  # Use the existing thread pool shutdown
            if hasattr(app, 'pipeline_manager'):
                app.pipeline_manager.cleanup()
            if hasattr(app, 'engine'):
                cleanup_db(app.engine)

        logger.info(f"Application initialized successfully in {config_name} mode")
        return app

    except Exception as e:
        logger.error(f"Failed to create application: {str(e)}", exc_info=True)
        raise