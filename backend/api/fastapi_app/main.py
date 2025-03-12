# backend/api/fastapi_app/main.py

import os
import logging
import uvicorn
from pathlib import Path
from typing import Tuple, Optional
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from ..app import ApplicationFactory

# Declare the global app variable
app: Optional[FastAPI] = None

def configure_logging() -> logging.Logger:
    """Configure application logging."""
    log_dir = Path(__file__).parent.parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'fastapi_app.log'),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)


def load_environment() -> Tuple[str, int, str]:
    """Load and validate environment variables."""
    env_path = Path(__file__).parent.parent.parent / '.env'
    load_dotenv(env_path)

    env = os.getenv('ENVIRONMENT', 'development').lower()
    try:
        port = int(os.getenv('PORT', '8000'))
    except ValueError:
        raise ValueError("PORT must be a valid integer")

    host = os.getenv('HOST', '0.0.0.0')

    valid_environments = ['development', 'testing', 'production']
    if env not in valid_environments:
        raise ValueError(f"Invalid environment: {env}. Must be one of {valid_environments}")

    return env, port, host


def create_application(env: str) -> FastAPI:
    """Create and configure the FastAPI application."""
    # Create application using factory
    app_factory = ApplicationFactory()
    application = app_factory.create_app(env)

    # Add security middleware for production
    if env == 'production':
        application.add_middleware(HTTPSRedirectMiddleware)

        allowed_hosts = os.getenv('ALLOWED_HOSTS', '*').split(',')
        application.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts
        )

        @application.middleware("http")
        async def add_security_headers(request, call_next):
            response = await call_next(request)
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            return response

    return application


def init_app() -> FastAPI:
    """Initialize the application for ASGI servers."""
    logger = configure_logging()
    try:
        env, _, _ = load_environment()
        return create_application(env)
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}", exc_info=True)
        raise


def main():
    """Primary application initialization and execution."""
    logger = configure_logging()

    try:
        # Load environment configuration
        env, port, host = load_environment()
        debug = env == 'development'

        logger.info(f"Starting server in {env} mode")
        logger.info(f"Host: {host}, Port: {port}, Debug: {debug}")

        if debug:
            logger.warning("Debug mode is enabled - do not use in production!")

        # Create and configure application
        application = create_application(env)

        if env == 'production':
            if debug:
                raise ValueError("Debug mode cannot be enabled in production")
            if host == '0.0.0.0':
                logger.warning("Using default host (0.0.0.0) in production")

        # Run application with uvicorn
        uvicorn.run(
            "api.fastapi_app.main:app",
            host=host,
            port=port,
            reload=debug,
            workers=4 if env == 'production' else 1,
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


# Initialize the application
app = init_app()

if __name__ == '__main__':
    main()