# backend/backend/api/fastapi_app/middleware/logging.py

import logging
import time
import os
from typing import Optional, Callable, Dict, Any

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


def configure_logging(app_name: str = "fastapi_app", log_level: Optional[str] = None) -> None:
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
    file_handler = logging.FileHandler('fastapi_app.log')
    file_handler.setFormatter(formatter)

    # Get the root logger
    logger = logging.getLogger(app_name)

    # Set log level
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear any existing handlers to prevent duplicate logs
    logger.handlers.clear()

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.info(f"Logging configured with level: {log_level}")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses

    Compatible with FastAPI/Starlette ASGI applications
    """

    def __init__(
            self,
            app: ASGIApp,
            logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the logging middleware

        Args:
            app (ASGIApp): The ASGI application
            logger (Optional[logging.Logger]): Custom logger.
                                              If None, uses default 'request_logger'
        """
        super().__init__(app)
        self.logger = logger or logging.getLogger('request_logger')

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log details about each incoming request and its processing time

        Args:
            request (Request): Incoming HTTP request
            call_next (Callable): Next middleware or request handler

        Returns:
            Response: HTTP response
        """
        # Start timer
        start_time = time.time()

        try:
            # Process the request
            response = await call_next(request)
        except Exception as exc:
            # Log any unexpected exceptions
            self.logger.exception(f"Unhandled exception: {exc}")
            raise
        finally:
            # Calculate request processing duration
            duration = time.time() - start_time

            # Log request details
            log_dict: Dict[str, Any] = {
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code,
                'duration': f'{duration:.2f}s'
            }

            # Log client information if available
            log_dict['client'] = request.client.host if request.client else 'Unknown'

            # Construct log message
            log_message = (
                f"Request: {log_dict['method']} {log_dict['path']} "
                f"Status: {log_dict['status_code']} "
                f"Client: {log_dict['client']} "
                f"Duration: {log_dict['duration']}"
            )

            # Log based on response status
            if response.status_code < 400:
                self.logger.info(log_message)
            elif 400 <= response.status_code < 500:
                self.logger.warning(log_message)
            else:
                self.logger.error(log_message)

        return response


__all__ = ['RequestLoggingMiddleware', 'configure_logging']