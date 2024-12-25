# flask_api/app/__init__.py

from flask import Flask, g, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    get_jwt_identity,
    get_jwt,
    verify_jwt_in_request
)
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

# Import auth manager
from .auth.jwt_manager import JWTTokenManager

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
                response.headers['Access-Control-Allow-Origin'] = 'http://localhost:5173'
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, Origin, X-Service'
                response.headers['Access-Control-Max-Age'] = '3600'
                return response
                
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

def register_blueprints(app: Flask) -> None:
    """Register all application blueprints with JWT protection."""
    try:
        # Import blueprints
        from backend.flask_api.app.blueprints.auth.routes import auth_bp
        from backend.flask_api.app.blueprints.data_sources.routes import data_source_bp
        from backend.flask_api.app.blueprints.pipeline.routes import pipeline_bp
        from backend.flask_api.app.blueprints.analysis.routes import analysis_bp
        from backend.flask_api.app.blueprints.recommendations.routes import recommendation_bp
        from backend.flask_api.app.blueprints.decisions.routes import decision_bp
        from backend.flask_api.app.blueprints.monitoring.routes import monitoring_bp
        from backend.flask_api.app.blueprints.reports.routes import reports_bp
        from backend.flask_api.app.blueprints.settings.routes import settings_bp
        from flask_jwt_extended import jwt_required

        # Define public blueprints (no JWT required)
        public_blueprints = [
            (auth_bp, '/api/v1/auth'),  # Auth routes should be public
        ]

        # Define protected blueprints (JWT required)
        protected_blueprints = [
            (data_source_bp, '/api/v1/sources'),
            (pipeline_bp, '/pipelines'),
            (analysis_bp, '/api/v1/analysis'),
            (recommendation_bp, '/api/v1/recommendations'),
            (decision_bp, '/api/v1/decisions'),
            (monitoring_bp, '/api/v1/monitoring'),
            (reports_bp, '/api/v1/reports'),
            (settings_bp, '/api/v1/settings')
        ]

        # Register public blueprints
        for blueprint, url_prefix in public_blueprints:
            try:
                app.register_blueprint(blueprint, url_prefix=url_prefix)
                logger.info(f"Registered public blueprint: {blueprint.name} at {url_prefix}")
            except Exception as e:
                logger.error(f"Failed to register public blueprint {blueprint.name}: {str(e)}")
                raise

        # Register protected blueprints with JWT
        for blueprint, url_prefix in protected_blueprints:
            try:
                # Apply JWT protection to all routes in blueprint
                for view_function in blueprint.view_functions.values():
                    # Ensure we don't double-wrap if jwt_required is already present
                    if not hasattr(view_function, '_jwt_required'):
                        protected_view = jwt_required()(view_function)
                        protected_view._jwt_required = True  # Mark as protected
                        blueprint.view_functions[view_function.__name__] = protected_view

                app.register_blueprint(blueprint, url_prefix=url_prefix)
                logger.info(f"Registered protected blueprint: {blueprint.name} at {url_prefix}")
            except Exception as e:
                logger.error(f"Failed to register protected blueprint {blueprint.name}: {str(e)}")
                raise

        # Register default routes
        @app.route('/')
        def index():
            return {
                'status': 'ok',
                'message': 'Enterprise Pipeline API',
                'version': '1.0.0'
            }

        @app.route('/health')
        def health_check():
            return {
                'status': 'healthy',
                'services': {
                    'database': 'up',
                    'pipeline': 'up'
                }
            }

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
        
        # Configure components in order
        configure_logging(app)
        _configure_paths(app)
        _init_extensions(app)
        _init_jwt(app)  # Initialize JWT before blueprints
        _init_database(app)
        register_error_handlers(app)
        register_blueprints(app)
        
        # Add request logging middleware
        app.wsgi_app = RequestLoggingMiddleware(app.wsgi_app)
        
        logger.info(f"Application initialized successfully in {config_name} mode")
        return app
        
    except Exception as e:
        logger.error(f"Failed to create application: {str(e)}", exc_info=True)
        raise