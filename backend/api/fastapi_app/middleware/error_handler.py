# backend/api/fastapi_app/middleware/error_handling.py

import logging
from typing import Dict, Any, Optional, Union

from fastapi import Request, HTTPException
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

class ErrorResponse:
    """Standardized error response formatting."""

    @staticmethod
    def create(
        code: int,
        name: str,
        description: str,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """
        Create a standardized error response.

        Args:
            code: HTTP status code
            name: Error name or title
            description: Detailed error description
            additional_info: Optional additional error details

        Returns:
            JSONResponse with standardized error format
        """
        response_data = {
            'error': {
                'code': code,
                'name': name,
                'description': description
            }
        }

        if additional_info:
            response_data['error'].update(additional_info)

        return JSONResponse(
            status_code=code,
            content=response_data
        )

class GlobalErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for global error handling and logging
    """
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Global error handling middleware

        Args:
            request: Incoming request
            call_next: Next middleware or request handler

        Returns:
            Response from the request handler
        """
        try:
            response = await call_next(request)
            return response

        except HTTPException as http_exc:
            # Handle known HTTP exceptions
            logger.error(f"HTTP Error: {http_exc.status_code} - {http_exc.detail}")
            return ErrorResponse.create(
                http_exc.status_code,
                http_exc.detail,
                str(http_exc.detail)
            )

        except Exception as exc:
            # Handle unexpected errors
            logger.error("Unhandled error", exc_info=True)
            return ErrorResponse.create(
                HTTP_500_INTERNAL_SERVER_ERROR,
                'Internal Server Error',
                'An unexpected error occurred.'
            )

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

def custom_route_handler(route: APIRoute) -> APIRoute:
    """
    Custom route handler to enhance error handling and logging

    Args:
        route: Original FastAPI route

    Returns:
        Modified route with enhanced error handling
    """
    original_handler = route.endpoint

    async def custom_handler(*args, **kwargs):
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

    route.endpoint = custom_handler
    return route

def register_error_handlers(app):
    """
    Register comprehensive error handlers for the FastAPI application.

    Args:
        app: FastAPI application instance

    Returns:
        Modified FastAPI application with error handlers
    """
    # Add global error handling middleware
    app.add_middleware(GlobalErrorHandlingMiddleware)

    # Custom exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        Global HTTP exception handler

        Args:
            request: Incoming request
            exc: HTTP exception

        Returns:
            Standardized error response
        """
        logger.error(
            f"HTTP Error: {exc.status_code} - {exc.detail} "
            f"Path: {request.url.path}"
        )

        return ErrorResponse.create(
            exc.status_code,
            exc.detail,
            str(exc.detail)
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """
        Global generic exception handler

        Args:
            request: Incoming request
            exc: Unexpected exception

        Returns:
            Standardized error response
        """
        logger.error(
            f"Unhandled error: {str(exc)} "
            f"Path: {request.url.path}",
            exc_info=True
        )

        return ErrorResponse.create(
            HTTP_500_INTERNAL_SERVER_ERROR,
            'Internal Server Error',
            'An unexpected error occurred.'
        )

    # Modify all routes for enhanced error handling
    for route in app.routes:
        if isinstance(route, APIRoute):
            route = custom_route_handler(route)

    logger.info("Error handlers registered successfully")
    return app