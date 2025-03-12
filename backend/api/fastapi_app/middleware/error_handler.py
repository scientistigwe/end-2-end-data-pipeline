# api/fastapi_app/middleware/error_handling.py

import logging
from typing import Dict, Any, Optional, Type
from fastapi import Request, HTTPException, FastAPI
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE
)

# Configure logger
logger = logging.getLogger(__name__)


class ErrorDetail:
    """Standardized error detail structure"""

    def __init__(
            self,
            code: int,
            message: str,
            error_type: str,
            details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.error_type = error_type
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        """Convert error detail to dictionary format"""
        error_dict = {
            "code": self.code,
            "message": self.message,
            "type": self.error_type
        }
        if self.details:
            error_dict["details"] = self.details
        return {"error": error_dict}


class ErrorHandler:
    """Centralized error handling logic"""

    @staticmethod
    def create_error_response(error_detail: ErrorDetail) -> JSONResponse:
        """Create standardized JSON response for errors"""
        return JSONResponse(
            status_code=error_detail.code,
            content=error_detail.to_dict()
        )

    @staticmethod
    def handle_http_exception(exc: HTTPException) -> JSONResponse:
        """Handle FastAPI HTTP exceptions"""
        error_detail = ErrorDetail(
            code=exc.status_code,
            message=str(exc.detail),
            error_type="http_error",
            details=getattr(exc, "headers", None)
        )
        logger.error(f"HTTP Exception: {exc.detail}", exc_info=True)
        return ErrorHandler.create_error_response(error_detail)

    @staticmethod
    def handle_validation_error(exc: Exception) -> JSONResponse:
        """Handle Pydantic validation errors"""
        error_detail = ErrorDetail(
            code=HTTP_422_UNPROCESSABLE_ENTITY,
            message="Validation error",
            error_type="validation_error",
            details={"errors": str(exc)}
        )
        logger.error(f"Validation Error: {exc}", exc_info=True)
        return ErrorHandler.create_error_response(error_detail)

    @staticmethod
    def handle_generic_exception(exc: Exception, request: Request) -> JSONResponse:
        """Handle generic unhandled exceptions"""
        error_detail = ErrorDetail(
            code=HTTP_500_INTERNAL_SERVER_ERROR,
            message="Internal server error",
            error_type="server_error",
            details={"path": str(request.url.path)} if request else None
        )
        logger.critical(
            f"Unhandled error processing request: {str(exc)}",
            exc_info=True
        )
        return ErrorHandler.create_error_response(error_detail)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware"""

    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.error_handler = ErrorHandler()

    async def dispatch(
            self,
            request: Request,
            call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            response = await call_next(request)
            return response

        except HTTPException as exc:
            return self.error_handler.handle_http_exception(exc)

        except Exception as exc:
            return self.error_handler.handle_generic_exception(exc, request)


class RouteErrorHandler:
    """Enhanced error handling for individual routes"""

    @staticmethod
    def wrap_route(route: APIRoute) -> APIRoute:
        """Wrap route with enhanced error handling"""
        original_handler = route.endpoint

        async def wrapped_handler(*args, **kwargs):
            try:
                return await original_handler(*args, **kwargs)
            except HTTPException as http_exc:
                logger.error(
                    f"HTTP Error in {route.endpoint.__name__}: "
                    f"{http_exc.status_code} - {http_exc.detail}"
                )
                raise
            except Exception as exc:
                logger.error(
                    f"Unhandled error in {route.endpoint.__name__}",
                    exc_info=True
                )
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='An unexpected error occurred.'
                )

        route.endpoint = wrapped_handler
        return route


def setup_error_handling(app: FastAPI) -> None:
    """
    Configure comprehensive error handling for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Add global error handling middleware
    app.add_middleware(ErrorHandlingMiddleware)

    # Register exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return ErrorHandler.handle_http_exception(exc)

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return ErrorHandler.handle_generic_exception(exc, request)

    # Enhance all routes with additional error handling
    for route in app.routes:
        if isinstance(route, APIRoute):
            RouteErrorHandler.wrap_route(route)

    logger.info("Error handling configuration completed successfully")


def create_cors_headers(origin: Optional[str] = None) -> Dict[str, str]:
    """
    Create CORS headers for responses.

    Args:
        origin: Optional origin to allow

    Returns:
        Dictionary of CORS headers
    """
    return {
        'Access-Control-Allow-Origin': origin or '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Max-Age': '3600'
    }