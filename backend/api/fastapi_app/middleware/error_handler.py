"""
Error handling middleware for Flask application.
Provides comprehensive HTTP error handling and request validation.
"""

from flask import request, jsonify, current_app
from werkzeug.exceptions import HTTPException
import logging
from typing import Dict, Any, Tuple, Optional

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
    ) -> Tuple[Dict[str, Any], int]:
        """
        Create a standardized error response.

        Args:
            code: HTTP status code
            name: Error name or title
            description: Detailed error description
            additional_info: Optional additional error details

        Returns:
            Tuple of (response_dict, status_code)
        """
        response = {
            'error': {
                'code': code,
                'name': name,
                'description': description
            }
        }

        if additional_info:
            response['error'].update(additional_info)

        return jsonify(response), code


def create_cors_headers(origin: Optional[str] = None) -> Dict[str, str]:
    """
    Create CORS headers for responses.

    Args:
        origin: Optional origin to allow

    Returns:
        Dictionary of CORS headers
    """
    return {
        'Access-Control-Allow-Origin': origin or request.headers.get('Origin', '*'),
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Max-Age': '3600'
    }


def handle_preflight() -> Tuple[Dict[str, str], int]:
    """
    Handle preflight OPTIONS requests with appropriate CORS headers.

    Returns:
        Tuple of (response, status_code)
    """
    response = jsonify({'message': 'OK'})
    response.headers.update(create_cors_headers())
    return response, 200


def register_error_handlers(app):
    """
    Register comprehensive error handlers for the Flask application.

    Args:
        app: Flask application instance

    Returns:
        Modified Flask application with error handlers
    """

    @app.before_request
    def validate_request_method():
        """Validate HTTP method for current request."""
        if request.method == 'OPTIONS':
            return handle_preflight()

        try:
            adapter = current_app.url_map.bind_to_environ(request.environ)
            adapter.match()

        except HTTPException as e:
            if e.code == 405:
                logger.warning(
                    "Method not allowed: %s %s. Allowed methods: %s",
                    request.method,
                    request.path,
                    ', '.join(e.valid_methods)
                )

                response = jsonify({
                    'error': {
                        'code': 405,
                        'name': 'Method Not Allowed',
                        'description': f'The method {request.method} is not allowed for this endpoint.',
                        'allowed_methods': list(e.valid_methods)
                    }
                })
                response.status_code = 405
                response.headers['Allow'] = ', '.join(e.valid_methods)
                return response

            # Let Flask handle other HTTP exceptions
            raise

    def register_http_error_handler(error_code: int, name: str, description: str):
        """
        Register handler for specific HTTP error code.

        Args:
            error_code: HTTP status code to handle
            name: Error name
            description: Default error description
        """

        @app.errorhandler(error_code)
        def handle_error(error):
            logger.error("%s error: %s", name, error)
            return ErrorResponse.create(
                error_code,
                name,
                getattr(error, 'description', description)
            )

    # Register handlers for common HTTP errors
    error_definitions = {
        400: ('Bad Request', 'The request was invalid or malformed.'),
        401: ('Unauthorized', 'Authentication is required to access this resource.'),
        403: ('Forbidden', 'You do not have permission to access this resource.'),
        404: ('Not Found', 'The requested resource was not found.'),
        405: ('Method Not Allowed', 'The HTTP method is not allowed for this endpoint.'),
        422: ('Unprocessable Entity', 'The request data was invalid.'),
        429: ('Too Many Requests', 'Rate limit exceeded. Please try again later.'),
        500: ('Internal Server Error', 'An unexpected error occurred on the server.'),
        503: ('Service Unavailable', 'The service is temporarily unavailable.')
    }

    for code, (name, description) in error_definitions.items():
        register_http_error_handler(code, name, description)

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        """Handle any unregistered HTTP exceptions."""
        logger.error("HTTP error occurred: %s", error)
        return ErrorResponse.create(
            error.code,
            error.name,
            error.description
        )

    @app.errorhandler(Exception)
    def handle_generic_error(error):
        """Handle all unhandled exceptions."""
        logger.error("Unhandled error occurred: %s", str(error), exc_info=True)
        return ErrorResponse.create(
            500,
            'Internal Server Error',
            'An unexpected error occurred.'
        )

    logger.info("Error handlers registered successfully")
    return app