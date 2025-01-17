# backend\backend\api\main.py
"""Application Entry Point"""
import os
import logging
from pathlib import Path
from typing import Tuple
from dotenv import load_dotenv
from flask_api.app import create_app

def configure_logging() -> logging.Logger:
    """Configure application logging.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging format and handlers
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # File handler for persistent logging
            logging.FileHandler(log_dir / 'app.log'),
            # Stream handler for console output
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def load_environment() -> Tuple[str, int, str]:
    """Load and validate environment variables.
    
    Returns:
        Tuple[str, int, str]: Environment name, port number, and host
        
    Raises:
        ValueError: If required environment variables are missing or invalid
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Get environment settings with defaults
    env = os.getenv('FLASK_ENV', 'development').lower()
    
    try:
        port = int(os.getenv('PORT', '5000'))
    except ValueError:
        raise ValueError("PORT must be a valid integer")
        
    host = os.getenv('HOST', '0.0.0.0')
    
    # Validate environment
    valid_environments = ['development', 'testing', 'production']
    if env not in valid_environments:
        raise ValueError(f"Invalid environment: {env}. Must be one of {valid_environments}")
    
    return env, port, host

def main():
    """Primary application initialization and execution."""
    logger = configure_logging()
    
    try:
        # Load environment configuration
        env, port, host = load_environment()
        
        # Set debug mode based on environment
        debug = env == 'development'
        
        # Log startup information
        logger.info(f"Starting server in {env} mode")
        logger.info(f"Host: {host}, Port: {port}, Debug: {debug}")
        
        if debug:
            logger.warning("Debug mode is enabled - do not use in production!")
        
        # Create and configure application
        app = create_app(env)
        
        if env == 'production':
            # Production-specific checks
            if debug:
                raise ValueError("Debug mode cannot be enabled in production")
            if host == '0.0.0.0':
                logger.warning("Using default host (0.0.0.0) in production")
        
        # Additional security headers for production
        if env == 'production':
            @app.after_request
            def add_security_headers(response):
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
                response.headers['X-Content-Type-Options'] = 'nosniff'
                response.headers['X-Frame-Options'] = 'SAMEORIGIN'
                response.headers['X-XSS-Protection'] = '1; mode=block'
                return response
        
        # Run application
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug,  # Only use reloader in debug mode
            threaded=True
        )
        
    except ValueError as ve:
        logger.error(f"Configuration error: {str(ve)}")
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        raise SystemExit(1)
    finally:
        logger.info("Application shutdown complete")

if __name__ == '__main__':
    main()