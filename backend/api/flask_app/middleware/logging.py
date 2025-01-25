# backend\backend\api\flask_app\middleware\logging.py
import logging
import time
from flask import request, g
from typing import Optional
import os

def configure_logging(app_name: str = "flask_app", log_level: Optional[str] = None) -> None:
    """Configure logging for the application."""
    # Set default log level if none provided
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO')

    # Create formatters and handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # File handler
    file_handler = logging.FileHandler('flask_app.log')
    file_handler.setFormatter(formatter)

    # Get the root logger
    logger = logging.getLogger(app_name)
    
    # Set log level
    logger.setLevel(getattr(logging, log_level.upper()))

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.info(f"Logging configured with level: {log_level}")

class RequestLoggingMiddleware:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger('request_logger')

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD', '')

        # Start timer
        start_time = time.time()

        def custom_start_response(status, headers, exc_info=None):
            duration = time.time() - start_time
            status_code = int(status.split()[0])

            self.logger.info(
                f"Request: {method} {path} "
                f"Status: {status_code} "
                f"Duration: {duration:.2f}s"
            )
            return start_response(status, headers, exc_info)

        return self.app(environ, custom_start_response)

__all__ = ['RequestLoggingMiddleware', 'configure_logging']