# flask_api/app/__init__.py

from flask import Flask, g, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

# Import configurations
from backend.flask_api.config import get_config
from backend.database.config import init_db

# Import middleware
from .middleware.error_handler import register_error_handlers
from .middleware.logging import RequestLoggingMiddleware

logger = logging.getLogger(__name__)

# Initialize SQLAlchemy instance
db = SQLAlchemy()

def configure_logging(app: Flask) -> None:
    """Configure application logging.
    
    Args:
        app: Flask application instance
    """
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
                         "X-Service",  # Added this
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
                # Handle OPTIONS requests specifically
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
def _init_database(app: Flask) -> Tuple[Any, Any]:
    """Initialize database connection and session management.
    
    Args:
        app: Flask application instance
        
    Returns:
        Tuple containing database engine and session factory
    """
    try:
        # Initialize SQLAlchemy with app
        engine, SessionLocal = init_db(app)
        
        # Add database session management
        @app.before_request
        def before_request():
            g.db = SessionLocal()

        @app.teardown_appcontext
        def teardown_db(exc):
            db = g.pop('db', None)
            if db is not None:
                db.close()
                
        # Create all tables
        from backend.database.models import Base
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database initialized successfully")
        return engine, SessionLocal
        
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}", exc_info=True)
        raise

def _configure_paths(app: Flask) -> None:
    """Configure application paths for uploads and logs.
    
    Args:
        app: Flask application instance
    """
    try:
        for folder in ['UPLOAD_FOLDER', 'LOG_FOLDER']:
            directory = Path(app.config[folder])
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info("Application paths configured successfully")
        
    except Exception as e:
        logger.error(f"Path configuration error: {str(e)}", exc_info=True)
        raise

def register_blueprints(app: Flask) -> None:
    """Register all application blueprints.
    
    Args:
        app: Flask application instance
    """
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

        # Blueprint registration with error handling
        blueprints = [
            (auth_bp, '/api/v1/auth'),
            (data_source_bp, '/api/v1/sources'),
            (pipeline_bp, '/api/v1/pipelines'),
            (analysis_bp, '/api/v1/analysis'),
            (recommendation_bp, '/api/v1/recommendations'),
            (decision_bp, '/api/v1/decisions'),
            (monitoring_bp, '/api/v1/monitoring'),
            (reports_bp, '/api/v1/reports'),
            (settings_bp, '/api/v1/settings')
        ]

        # Register each blueprint with proper error handling
        for blueprint, url_prefix in blueprints:
            try:
                app.register_blueprint(blueprint, url_prefix=url_prefix)
                logger.info(f"Registered blueprint: {blueprint.name} at {url_prefix}")
            except Exception as e:
                logger.error(f"Failed to register blueprint {blueprint.name}: {str(e)}")
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
    """Application factory function.
    
    Args:
        config_name: Configuration environment name
        
    Returns:
        Configured Flask application instance
    """
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