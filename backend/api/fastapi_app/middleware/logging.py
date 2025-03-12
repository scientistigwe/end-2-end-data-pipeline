# api/fastapi_app/middleware/logging.py

import logging
import time
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses"""

    def __init__(self, app, log_level: str = 'INFO'):
        super().__init__(app)
        self.log_level = getattr(logging, log_level.upper())
        logger.setLevel(self.log_level)

    async def dispatch(
            self,
            request: Request,
            call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()

        # Process the request and get response
        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Create log message
            status_code = response.status_code
            log_msg = (
                f"{request.method} {request.url.path} "
                f"[{status_code}] "
                f"took {process_time:.2f}s "
                f"- {request.client.host if request.client else 'Unknown'}"
            )

            # Log based on status code
            if status_code >= 500:
                logger.error(log_msg)
            elif status_code >= 400:
                logger.warning(log_msg)
            else:
                logger.info(log_msg)

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"took {process_time:.2f}s - Error: {str(e)}"
            )
            raise

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


__all__ = ['RequestLoggingMiddleware', 'configure_logging']