# flask_api/app/__init__.py

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import logging
from pathlib import Path
from typing import Dict, Any

# Import configurations
from .config import Config
from ..database.config import init_db

# Import middleware
from .middleware.error_handler import register_error_handlers
from .middleware.logging import configure_logging

# Import routes registry
from .routes import register_blueprints

logger = logging.getLogger(__name__)

def create_app(config_name: str = 'development') -> Flask:
    """
    Application factory function.
    
    Args:
        config_name (str): Configuration environment name
        
    Returns:
        Flask: Configured Flask application instance
    """
    try:
        # Initialize Flask app
        app = Flask(__name__)
        
        # Load configuration
        app_config = Config(config_name)
        app.config.from_object(app_config)
        
        # Configure logging
        configure_logging(app)
        
        # Initialize extensions
        _init_extensions(app)
        
        # Initialize database
        _init_database(app)
        
        # Register error handlers
        register_error_handlers(app)
        
        # Register blueprints
        register_blueprints(app)
        
        logger.info(f"Application initialized successfully in {config_name} mode")
        return app
        
    except Exception as e:
        logger.error(f"Failed to create application: {str(e)}", exc_info=True)
        raise

def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions"""
    try:
        # Initialize CORS
        CORS(app, resources={
            r"/api/*": {
                "origins": app.config['CORS_ORIGINS'],
                "methods": app.config['CORS_METHODS'],
                "allow_headers": app.config['CORS_HEADERS']
            }
        })
        
        # Initialize JWT
        jwt = JWTManager(app)
        
        @jwt.token_verification_failed_loader
        def token_verification_failed_callback(jwt_header, jwt_data):
            return {"message": "Token verification failed"}, 401
            
        @jwt.expired_token_loader
        def expired_token_callback(jwt_header, jwt_data):
            return {"message": "Token has expired"}, 401
            
        @jwt.invalid_token_loader
        def invalid_token_callback(error_string):
            return {"message": "Invalid token"}, 401
            
        logger.info("All extensions initialized successfully")
        
    except Exception as e:
        logger.error(f"Extension initialization error: {str(e)}", exc_info=True)
        raise

def _init_database(app: Flask) -> None:
    """Initialize database connection"""
    try:
        # Initialize SQLAlchemy with app
        engine, session = init_db(app)
        
        # Add session to app context
        app.db_session = session
        
        # Create all tables
        from ..database.models import Base
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}", exc_info=True)
        raise

def _configure_paths(app: Flask) -> None:
    """Configure application paths"""
    try:
        # Set up upload directory
        uploads_dir = Path(app.root_path) / 'uploads'
        uploads_dir.mkdir(exist_ok=True)
        app.config['UPLOAD_FOLDER'] = str(uploads_dir)
        
        # Set up logs directory
        logs_dir = Path(app.root_path) / 'logs'
        logs_dir.mkdir(exist_ok=True)
        app.config['LOG_FOLDER'] = str(logs_dir)
        
        logger.info("Application paths configured successfully")
        
    except Exception as e:
        logger.error(f"Path configuration error: {str(e)}", exc_info=True)
        raise

# Initialize SQLAlchemy instance
# This should be imported by models
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()