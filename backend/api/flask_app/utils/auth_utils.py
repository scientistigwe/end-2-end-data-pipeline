from functools import wraps
from flask import g, request, current_app
from typing import Callable, Any
from ..utils.response_builder import ResponseBuilder


def login_required(f: Callable) -> Callable:
    """
    Decorator to verify user is logged in.

    Args:
        f: Function to decorate

    Returns:
        Decorated function that checks for authenticated user
    """

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not hasattr(g, 'current_user') or not g.current_user:
            return ResponseBuilder.error(
                "Authentication required",
                status_code=401
            )
        return f(*args, **kwargs)

    return decorated_function


def role_required(role: str) -> Callable:
    """
    Decorator to verify user has required role.

    Args:
        role: Required role name

    Returns:
        Decorated function that checks for role authorization
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            if not hasattr(g, 'current_user') or not g.current_user:
                return ResponseBuilder.error(
                    "Authentication required",
                    status_code=401
                )

            if not hasattr(g.current_user, 'roles') or role not in g.current_user.roles:
                return ResponseBuilder.error(
                    "Insufficient permissions",
                    status_code=403
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f: Callable) -> Callable:
    """
    Decorator to verify user has admin role.

    Args:
        f: Function to decorate

    Returns:
        Decorated function that checks for admin authorization
    """

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not hasattr(g, 'current_user') or not g.current_user:
            return ResponseBuilder.error(
                "Authentication required",
                status_code=401
            )

        if not hasattr(g.current_user, 'roles') or 'admin' not in g.current_user.roles:
            return ResponseBuilder.error(
                "Admin access required",
                status_code=403
            )

        return f(*args, **kwargs)

    return decorated_function


def verify_api_key() -> Callable:
    """
    Decorator to verify API key for service-to-service communication.

    Returns:
        Decorated function that checks for valid API key
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                return ResponseBuilder.error(
                    "API key required",
                    status_code=401
                )

            valid_api_keys = current_app.config.get('API_KEYS', set())
            if api_key not in valid_api_keys:
                return ResponseBuilder.error(
                    "Invalid API key",
                    status_code=403
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator