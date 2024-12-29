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
from backend.flask_api.config import get_config
from backend.database.config import init_db

# Import middleware
from .middleware.error_handler import register_error_handlers
from .middleware.logging import RequestLoggingMiddleware
from .middleware.auth_middleware import auth_middleware

# Import auth manager
from .auth.jwt_manager import JWTTokenManager

# Import all services
from .services.auth.auth_service import AuthService
from .services.data_sources.file_service import FileSourceService
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

logger = logging.getLogger(__name__)

# Initialize SQLAlchemy instance
db = SQLAlchemy()

def configure_logging(app: Flask) -> None:
    """Configure application logging."""
    log_dir = Path(app.config['LOG_FOLDER'])
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'app.log'),
            logging.StreamHandler()
        ]
    )

def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions"""
    try:
        CORS(app, 
             resources={
                 r"/api/*": {
                     "origins": ["http://localhost:5173"],
                     "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                     "allow_headers": [
                         "Content-Type",
                         "Authorization",
                         "X-Requested-With",
                         "Accept",
                         "Origin",
                         "X-Service",
                         "Access-Control-Request-Method",
                         "Access-Control-Request-Headers"
                     ],
                     "expose_headers": ["Content-Type", "Authorization"],
                     "supports_credentials": True,
                     "max_age": 3600,
                     "send_wildcard": False,
                     "automatic_options": True
                 }
             })

        @app.after_request
        def after_request(response):
            if request.method == 'OPTIONS':
                response.status_code = 200
                response.headers.update({
                    'Access-Control-Allow-Origin': 'http://localhost:5173',
                    'Access-Control-Allow-Credentials': 'true',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin, X-Service',
                    'Access-Control-Max-Age': '3600'
                })
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
        engine, SessionLocal = init_db(app)
        
        @app.before_request
        def before_request():
            g.db = SessionLocal()

        @app.teardown_appcontext
        def teardown_db(exc):
            db = g.pop('db', None)
            if db is not None:
                db.close()
                
        from backend.database.models import Base
        Base.metadata.create_all(bind=engine)
        
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

def _initialize_services(app: Flask, db_session) -> None:
    """Initialize all application services."""
    try:
        app.services = {
            'auth_service': AuthService(db_session),
            'file_service': FileSourceService(db_session),
            'db_service': DatabaseSourceService(db_session),
            's3_service': S3SourceService(db_session),
            'api_service': APISourceService(db_session),
            'stream_service': StreamSourceService(db_session),
            'pipeline_service': PipelineService(db_session),
            'quality_service': QualityService(db_session),
            'insight_service': InsightService(db_session),
            'recommendation_service': RecommendationService(db_session),
            'decision_service': DecisionService(db_session),
            'monitoring_service': MonitoringService(db_session),
            'report_service': ReportService(db_session),
            'settings_service': SettingsService(db_session)
        }
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Service initialization error: {str(e)}", exc_info=True)
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

        # Define blueprints
        public_blueprints = [
            (create_auth_blueprint(
                auth_service=app.services['auth_service'],
                db_session=db_session
            ), '/api/v1/auth'),
        ]

        protected_blueprints = [
            (create_data_source_blueprint(
                file_service=app.services['file_service'],
                db_service=app.services['db_service'],
                s3_service=app.services['s3_service'],
                api_service=app.services['api_service'],
                stream_service=app.services['stream_service'],
                db_session=db_session
            ), '/api/v1/sources'),
            (create_pipeline_blueprint(
                pipeline_service=app.services['pipeline_service'],
                db_session=db_session
            ), '/api/v1/pipelines'),
            (create_analysis_blueprint(
                quality_service=app.services['quality_service'],
                insight_service=app.services['insight_service'],
                db_session=db_session
            ), '/api/v1/analysis'),
            (create_recommendation_blueprint(
                recommendation_service=app.services['recommendation_service'],
                db_session=db_session
            ), '/api/v1/recommendations'),
            (create_decision_blueprint(
                decision_service=app.services['decision_service'],
                db_session=db_session
            ), '/api/v1/decisions'),
            (create_monitoring_blueprint(
                monitoring_service=app.services['monitoring_service'],
                db_session=db_session
            ), '/api/v1/monitoring'),
            (create_reports_blueprint(
                report_service=app.services['report_service'],
                db_session=db_session
            ), '/api/v1/reports'),
            (create_settings_blueprint(
                settings_service=app.services['settings_service'],
                db_session=db_session
            ), '/api/v1/settings')
        ]

        # Register blueprints
        with app.app_context():
            # Register public blueprints
            for blueprint, url_prefix in public_blueprints:
                app.register_blueprint(blueprint, url_prefix=url_prefix)
                logger.info(f"Registered public blueprint at {url_prefix}")

            # Register protected blueprints
            for blueprint, url_prefix in protected_blueprints:
                # Apply JWT protection
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
        engine, SessionLocal = init_db(app)
        db_session = SessionLocal()
        
        # Initialize all services
        _initialize_services(app, db_session)
        
        # Register error handlers and blueprints
        register_error_handlers(app)
        with app.app_context():
            register_blueprints(app, db_session)
        
        # Add request logging middleware
        app.wsgi_app = RequestLoggingMiddleware(app.wsgi_app)
        
        # Add auth middleware
        app.before_request(auth_middleware())
        
        logger.info(f"Application initialized successfully in {config_name} mode")
        return app
        
    except Exception as e:
        logger.error(f"Failed to create application: {str(e)}", exc_info=True)
        raise