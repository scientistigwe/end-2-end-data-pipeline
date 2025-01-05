from functools import wraps
from flask import g, request, current_app, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from ..services.auth import AuthService
from typing import Optional
import logging
from contextlib import contextmanager
from ..utils.route_registry import APIRoutes, RouteDefinition

logger = logging.getLogger(__name__)

def normalize_route(path: str) -> str:
    """Normalize route by removing trailing slashes"""
    return path.rstrip('/')

def get_route_from_request(request_path: str, request_method: str) -> Optional[RouteDefinition]:
    """
    Match request path and method to defined API routes
    
    Args:
        request_path: The incoming request path
        request_method: The HTTP method used
        
    Returns:
        RouteDefinition if matched, None otherwise
        
    Time complexity: O(n) where n is number of routes
    Space complexity: O(1)
    """
    normalized_path = normalize_route(request_path)
    path_parts = normalized_path.split('/')
    
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
            return route_def
            
    return None

def debug_token():
    """
    Validate and debug Authorization header token
    
    Returns:
        bool: True if token is present and properly formatted
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        logger.error("No Authorization header found")
        return False
        
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        logger.error(f"Invalid Authorization header format: {auth_header}")
        return False
        
    logger.info(f"Token found in request: {parts[1][:10]}...")
    return True

@contextmanager
def get_db_session():
    """
    Context manager for database session handling
    
    Yields:
        Database session object
    """
    if hasattr(g, 'db'):
        yield g.db
    else:
        db = current_app.db
        g.db = db
        try:
            yield db
        finally:
            db.close()

def validate_and_get_user(user_id: str):
    """
    Validate user existence and set current user
    
    Args:
        user_id: User identifier from JWT
        
    Returns:
        Tuple of (success, response)
    """
    try:
        with get_db_session() as db:
            auth_service = AuthService(db)
            user = auth_service.get_user_by_id(user_id)
            if not user:
                logger.error(f"No user found for id: {user_id}")
                return False, (jsonify({"error": "User not found"}), 401)
            g.current_user = user
            return True, None
    except Exception as e:
        logger.error(f"Error validating user: {str(e)}", exc_info=True)
        return False, (jsonify({"error": "Authentication failed"}), 401)

def auth_middleware():
    """Authentication middleware using route registry"""
    def middleware():
        try:
            route_def = get_route_from_request(request.path, request.method)
            
            # Skip auth for unregistered routes or public routes
            if not route_def or not route_def.requires_auth:
                return None
                
            if not debug_token():
                return jsonify({"error": "Invalid or missing token"}), 401
                
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            if not user_id:
                logger.error("No user_id found in JWT token")
                return jsonify({"error": "Invalid token"}), 401
                
            success, response = validate_and_get_user(user_id)
            if not success:
                return response
                
        except Exception as e:
            logger.error(f"Middleware authentication error: {str(e)}", exc_info=True)
            return jsonify({"error": "Authentication failed"}), 401

    return middleware

def jwt_required_with_user():
    """Route decorator for JWT authentication with user context"""
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            try:
                route_def = get_route_from_request(request.path, request.method)
                
                # Skip auth for unregistered routes or public routes
                if route_def and not route_def.requires_auth:
                    return fn(*args, **kwargs)
                    
                if not debug_token():
                    return jsonify({"error": "Invalid or missing token"}), 401
                    
                verify_jwt_in_request()
                user_id = get_jwt_identity()
                
                if not user_id:
                    logger.error("No user_id found in JWT token")
                    return jsonify({"error": "Invalid token"}), 401
                
                success, response = validate_and_get_user(user_id)
                if not success:
                    return response
                    
                return fn(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Decorator authentication error: {str(e)}", exc_info=True)
                return jsonify({"error": "Authentication failed"}), 401
                
        return decorator
    return wrapper