from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from ..services.auth import AuthService
from typing import Optional, Tuple, Any
import logging
from contextlib import contextmanager
from ..utils.route_registry import APIRoutes, RouteDefinition
from flask import current_app, g
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from backend.docs.analyst_pa.backend.config import get_config  # Import your configuration


logger = logging.getLogger(__name__)

def normalize_route(path: str) -> str:
    """Normalize route by removing trailing slashes"""
    return path.rstrip('/')


def get_route_from_request(request_path: str, request_method: str) -> Optional[RouteDefinition]:
    """Match request path and method to defined API routes"""
    normalized_path = normalize_route(request_path)
    # Remove /api/v1 prefix if present
    if normalized_path.startswith('/api/v1'):
        normalized_path = normalized_path[7:]

    path_parts = normalized_path.split('/')
    logger.debug(f"Matching route: {normalized_path} [{request_method}]")

    for route in APIRoutes:
        route_def = route.value
        route_parts = route_def.path.split('/')

        if len(path_parts) != len(route_parts):
            continue

        matches = True
        for req_part, route_part in zip(path_parts, route_parts):
            if route_part.startswith('{') and route_part.endswith('}'):
                continue
            if req_part != route_part:
                matches = False
                break

        if matches and request_method in route_def.methods:
            logger.debug(f"Route matched: {route_def.path}")
            return route_def

    logger.debug("No matching route found")
    return None


@contextmanager
def get_db_session():
    """Context manager for db session handling"""
    if hasattr(g, 'db'):
        yield g.db
    else:
        try:
            # Try to get the configuration
            config = get_config('development')  # or use current_app.config
            
            # Create engine if not exists
            if not hasattr(current_app, 'engine'):
                current_app.engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
            
            # Create session factory
            Session = scoped_session(sessionmaker(bind=current_app.engine))
            
            try:
                session = Session()
                yield session
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error creating db session: {str(e)}")
            raise

def validate_and_get_user(user_id: str) -> Tuple[bool, Optional[Tuple[Any, int]]]:
    try:
        with get_db_session() as db_session:
            auth_service = AuthService(db_session)
            user = auth_service.get_user_by_id(user_id)
            if not user:
                logger.error(f"No user found for id: {user_id}")
                return False, (jsonify({
                    "error": "User not found",
                    "message": "The user associated with this token was not found"
                }), 401)
            g.current_user = user
            return True, None
    except Exception as e:
        logger.error(f"Error validating user: {str(e)}", exc_info=True)
        return False, (jsonify({
            "error": "Authentication failed",
            "message": "Failed to validate user credentials"
        }), 401)


def auth_middleware():
    """Authentication middleware using route registry"""

    def middleware():
        try:
            # Debug request information
            logger.debug(f"Request Path: {request.path}")
            logger.debug(f"Request Method: {request.method}")
            logger.debug(f"Request Cookies: {request.cookies}")
            logger.debug(f"Request Headers: {dict(request.headers)}")
            # Add detailed cookie logging
            logger.debug("All cookies present: %s", request.cookies.keys())
            logger.debug("JWT Config: %s", {
                key: value for key, value in current_app.config.items()
                if key.startswith('JWT_')
            })

            route_def = get_route_from_request(request.path, request.method)

            # Skip auth for unregistered routes or public routes
            if not route_def:
                logger.debug("Route not found in registry")
                return None

            if not route_def.requires_auth:
                logger.debug("Route does not require authentication")
                return None

            # Verify JWT from cookies
            try:
                verify_jwt_in_request(optional=False)
                logger.debug("JWT verification successful")
            except Exception as e:
                logger.error(f"JWT verification failed: {str(e)}", exc_info=True)
                return jsonify({
                    "error": "authorization_required",
                    "message": "Invalid or missing token",
                    "details": str(e)
                }), 401

            user_id = get_jwt_identity()
            logger.debug(f"JWT Identity: {user_id}")

            if not user_id:
                logger.error("No user_id found in JWT token")
                return jsonify({
                    "error": "invalid_token",
                    "message": "Token does not contain user identity"
                }), 401

            success, response = validate_and_get_user(user_id)
            if not success:
                return response

            logger.debug("Authentication successful")
            return None

        except Exception as e:
            logger.error(f"Middleware authentication error: {str(e)}", exc_info=True)
            return jsonify({
                "error": "authentication_failed",
                "message": "Authentication failed",
                "details": str(e)
            }), 401

    return middleware


def jwt_required_with_user():
    """Route decorator for JWT authentication with user context"""

    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            try:
                # Debug decorator information
                logger.debug(f"Protected route accessed: {request.path}")

                route_def = get_route_from_request(request.path, request.method)

                if route_def and not route_def.requires_auth:
                    logger.debug("Route is public, skipping authentication")
                    return fn(*args, **kwargs)

                try:
                    verify_jwt_in_request(optional=False)
                    logger.debug("JWT verification successful in decorator")
                except Exception as e:
                    logger.error(f"JWT verification failed in decorator: {str(e)}", exc_info=True)
                    return jsonify({
                        "error": "authorization_required",
                        "message": "Invalid or missing token",
                        "details": str(e)
                    }), 401

                user_id = get_jwt_identity()
                logger.debug(f"JWT Identity in decorator: {user_id}")

                if not user_id:
                    logger.error("No user_id found in JWT token")
                    return jsonify({
                        "error": "invalid_token",
                        "message": "Token does not contain user identity"
                    }), 401

                success, response = validate_and_get_user(user_id)
                if not success:
                    return response

                logger.debug("Authentication successful in decorator")
                return fn(*args, **kwargs)

            except Exception as e:
                logger.error(f"Decorator authentication error: {str(e)}", exc_info=True)
                return jsonify({
                    "error": "authentication_failed",
                    "message": "Authentication failed",
                    "details": str(e)
                }), 401

        return decorator

    return wrapper