# backend/api/main.py

import os
import logging
import uvicorn
from pathlib import Path
from typing import Tuple
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from api.app import ApplicationFactory


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
            logging.FileHandler(log_dir / 'fastapi_app.log'),
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
    env = os.getenv('ENVIRONMENT', 'development').lower()

    try:
        port = int(os.getenv('PORT', '8000'))
    except ValueError:
        raise ValueError("PORT must be a valid integer")

    host = os.getenv('HOST', '0.0.0.0')

    # Validate environment
    valid_environments = ['development', 'testing', 'production']
    if env not in valid_environments:
        raise ValueError(f"Invalid environment: {env}. Must be one of {valid_environments}")

    return env, port, host


def create_application(env: str) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        env (str): Environment name ('development', 'testing', or 'production')

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    # Create application using factory
    app_factory = ApplicationFactory()
    app = app_factory.create_app(env)

    # Add security middleware for production
    if env == 'production':
        # Force HTTPS redirect
        app.add_middleware(HTTPSRedirectMiddleware)

        # Add trusted host middleware
        allowed_hosts = os.getenv('ALLOWED_HOSTS', '*').split(',')
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts
        )

        # Add security headers middleware
        @app.middleware("http")
        async def add_security_headers(request, call_next):
            response = await call_next(request)
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            return response

    return app


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
        app = create_application(env)

        if env == 'production':
            # Production-specific checks
            if debug:
                raise ValueError("Debug mode cannot be enabled in production")
            if host == '0.0.0.0':
                logger.warning("Using default host (0.0.0.0) in production")

        # Run application with uvicorn
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=debug,  # Only use reload in debug mode
            workers=4 if env == 'production' else 1,  # Use multiple workers in production
            log_level="info",
            access_log=True
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