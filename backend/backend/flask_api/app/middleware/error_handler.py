from flask import jsonify
from werkzeug.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """Register error handlers for the application."""
    
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        """Handle all HTTP exceptions."""
        logger.error(f"HTTP error occurred: {error}")
        response = {
            'error': {
                'code': error.code,
                'name': error.name,
                'description': error.description,
            }
        }
        return jsonify(response), error.code

    @app.errorhandler(Exception)
    def handle_generic_error(error):
        """Handle all unhandled exceptions."""
        logger.error(f"Unhandled error occurred: {str(error)}", exc_info=True)
        response = {
            'error': {
                'code': 500,
                'name': 'Internal Server Error',
                'description': 'An unexpected error occurred.'
            }
        }
        return jsonify(response), 500

    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle bad request errors."""
        logger.error(f"Bad request error: {error}")
        response = {
            'error': {
                'code': 400,
                'name': 'Bad Request',
                'description': str(error.description)
            }
        }
        return jsonify(response), 400

    @app.errorhandler(401)
    def handle_unauthorized(error):
        """Handle unauthorized access errors."""
        logger.error(f"Unauthorized error: {error}")
        response = {
            'error': {
                'code': 401,
                'name': 'Unauthorized',
                'description': 'Authentication is required to access this resource.'
            }
        }
        return jsonify(response), 401

    @app.errorhandler(403)
    def handle_forbidden(error):
        """Handle forbidden access errors."""
        logger.error(f"Forbidden error: {error}")
        response = {
            'error': {
                'code': 403,
                'name': 'Forbidden',
                'description': 'You do not have permission to access this resource.'
            }
        }
        return jsonify(response), 403

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle not found errors."""
        logger.error(f"Not found error: {error}")
        response = {
            'error': {
                'code': 404,
                'name': 'Not Found',
                'description': 'The requested resource was not found.'
            }
        }
        return jsonify(response), 404

    @app.errorhandler(422)
    def handle_unprocessable_entity(error):
        """Handle validation errors."""
        logger.error(f"Validation error: {error}")
        response = {
            'error': {
                'code': 422,
                'name': 'Unprocessable Entity',
                'description': str(error.description),
                'errors': getattr(error, 'errors', None)
            }
        }
        return jsonify(response), 422

    @app.errorhandler(429)
    def handle_rate_limit(error):
        """Handle rate limit exceeded errors."""
        logger.error(f"Rate limit error: {error}")
        response = {
            'error': {
                'code': 429,
                'name': 'Too Many Requests',
                'description': 'Rate limit exceeded. Please try again later.'
            }
        }
        return jsonify(response), 429

    @app.errorhandler(500)
    def handle_server_error(error):
        """Handle internal server errors."""
        logger.error(f"Server error: {error}", exc_info=True)
        response = {
            'error': {
                'code': 500,
                'name': 'Internal Server Error',
                'description': 'An unexpected error occurred on the server.'
            }
        }
        return jsonify(response), 500

    @app.errorhandler(503)
    def handle_service_unavailable(error):
        """Handle service unavailable errors."""
        logger.error(f"Service unavailable error: {error}")
        response = {
            'error': {
                'code': 503,
                'name': 'Service Unavailable',
                'description': 'The service is temporarily unavailable.'
            }
        }
        return jsonify(response), 503

    logger.info("Error handlers registered successfully")