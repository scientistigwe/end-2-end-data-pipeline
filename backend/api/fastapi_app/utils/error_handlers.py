# fastapi_app/utils/error_handlers.py

import logging
from typing import Union, Optional, Any, Dict
from marshmallow import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import NotFound, HTTPException

from .response_builder import ResponseBuilder


def handle_validation_error(
        error: ValidationError,
        message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handle marshmallow validation errors with detailed error messages.

    Args:
        error (ValidationError): The validation error from marshmallow
        message (Optional[str]): Optional custom error message

    Returns:
        Dict[str, Any]: Formatted error response
    """
    error_messages = {}

    # Process nested validation errors
    for field, messages in error.messages.items():
        if isinstance(messages, dict):
            error_messages[field] = {}
            for nested_field, nested_messages in messages.items():
                error_messages[field][nested_field] = nested_messages[0] if isinstance(nested_messages,
                                                                                       list) else nested_messages
        else:
            error_messages[field] = messages[0] if isinstance(messages, list) else messages

    return ResponseBuilder.error(
        message=message or "Validation error",
        errors=error_messages,
        status_code=400
    )


def handle_service_error(
        error: Exception,
        message: str,
        logger: logging.Logger,
        status_code: int = 500
) -> Dict[str, Any]:
    """
    Handle service-level errors with proper logging.

    Args:
        error (Exception): The exception that occurred
        message (str): Error message for the client
        logger (logging.Logger): Logger instance for error tracking
        status_code (int): HTTP status code to return

    Returns:
        Dict[str, Any]: Formatted error response
    """
    error_details = {
        'type': error.__class__.__name__,
        'message': str(error)
    }

    # Log the error with traceback
    logger.error(
        f"{message}: {str(error)}",
        exc_info=True,
        extra={
            'error_type': error.__class__.__name__,
            'status_code': status_code
        }
    )

    # Special handling for SQLAlchemy errors
    if isinstance(error, SQLAlchemyError):
        message = "Database operation failed"
        status_code = 503  # Service Unavailable
        error_details['type'] = 'DatabaseError'

    # Handle HTTP exceptions
    if isinstance(error, HTTPException):
        status_code = error.code
        message = error.description

    return ResponseBuilder.error(
        message=message,
        errors=error_details,
        status_code=status_code
    )


def handle_not_found_error(
        error: Union[Exception, NotFound],
        message: str,
        logger: logging.Logger
) -> Dict[str, Any]:
    """
    Handle resource not found errors with custom messages.

    Args:
        error (Union[Exception, NotFound]): The not found error
        message (str): Custom message describing what wasn't found
        logger (logging.Logger): Logger instance for error tracking

    Returns:
        Dict[str, Any]: Formatted error response
    """
    error_details = {
        'type': 'ResourceNotFound',
        'resource': message
    }

    # Log the error without traceback for not found errors
    logger.warning(
        f"Resource not found: {message}",
        extra={
            'error_type': 'ResourceNotFound',
            'status_code': 404
        }
    )

    return ResponseBuilder.error(
        message=message,
        errors=error_details,
        status_code=404
    )


def handle_authorization_error(
        error: Exception,
        resource_type: str,
        resource_id: str,
        logger: logging.Logger
) -> Dict[str, Any]:
    """
    Handle authorization and permission errors.

    Args:
        error (Exception): The authorization error
        resource_type (str): Type of resource access was attempted on
        resource_id (str): ID of the resource
        logger (logging.Logger): Logger instance for error tracking

    Returns:
        Dict[str, Any]: Formatted error response
    """
    error_details = {
        'type': 'AuthorizationError',
        'resource_type': resource_type,
        'resource_id': resource_id
    }

    # Log the authorization failure
    logger.warning(
        f"Authorization failed for {resource_type} {resource_id}",
        extra={
            'error_type': 'AuthorizationError',
            'status_code': 403,
            'resource_type': resource_type,
            'resource_id': resource_id
        }
    )

    return ResponseBuilder.error(
        message=f"Not authorized to access {resource_type}",
        errors=error_details,
        status_code=403
    )


def handle_rate_limit_error(
        error: Exception,
        limit: int,
        window: int,
        logger: logging.Logger
) -> Dict[str, Any]:
    """
    Handle rate limiting errors with limit details.

    Args:
        error (Exception): The rate limit error
        limit (int): Rate limit threshold
        window (int): Time window in seconds
        logger (logging.Logger): Logger instance for error tracking

    Returns:
        Dict[str, Any]: Formatted error response
    """
    error_details = {
        'type': 'RateLimitError',
        'limit': limit,
        'window_seconds': window
    }

    # Log the rate limit violation
    logger.warning(
        f"Rate limit exceeded: {limit} requests per {window} seconds",
        extra={
            'error_type': 'RateLimitError',
            'status_code': 429,
            'limit': limit,
            'window': window
        }
    )

    return ResponseBuilder.error(
        message=f"Rate limit exceeded. Maximum {limit} requests per {window} seconds allowed.",
        errors=error_details,
        status_code=429
    )


def handle_dependency_error(
        error: Exception,
        service_name: str,
        logger: logging.Logger
) -> Dict[str, Any]:
    """
    Handle external service and dependency errors.

    Args:
        error (Exception): The dependency error
        service_name (str): Name of the failed service
        logger (logging.Logger): Logger instance for error tracking

    Returns:
        Dict[str, Any]: Formatted error response
    """
    error_details = {
        'type': 'DependencyError',
        'service': service_name,
        'message': str(error)
    }

    # Log the dependency failure
    logger.error(
        f"Dependency error with {service_name}: {str(error)}",
        exc_info=True,
        extra={
            'error_type': 'DependencyError',
            'status_code': 503,
            'service': service_name
        }
    )

    return ResponseBuilder.error(
        message=f"Service temporarily unavailable due to dependency error",
        errors=error_details,
        status_code=503
    )