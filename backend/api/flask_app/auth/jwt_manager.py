# backend/api/flask_app/auth/jwt_manager.py

from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    get_jwt,
    verify_jwt_in_request
)
from flask import current_app, jsonify, request
from datetime import timedelta, datetime
from typing import Dict, Any, Optional, Callable
from functools import wraps
import logging
from ..utils.route_registry import APIRoutes

logger = logging.getLogger(__name__)

refresh_path = APIRoutes.AUTH_REFRESH.value.path


class JWTTokenManager:
    """JWT Token management and authentication."""

    def __init__(self, app=None):
        self.jwt = JWTManager()
        self.blacklisted_tokens = set()  # Simple in-memory blacklist
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize JWT manager with application."""
        # JWT Configuration
        app.config.update({
            'JWT_SECRET_KEY': app.config['JWT_SECRET_KEY'],
            'JWT_ACCESS_TOKEN_EXPIRES': app.config['JWT_ACCESS_TOKEN_EXPIRES'],
            'JWT_REFRESH_TOKEN_EXPIRES': app.config['JWT_REFRESH_TOKEN_EXPIRES'],
            'JWT_ERROR_MESSAGE_KEY': 'message',
            'JWT_TOKEN_LOCATION': ['cookies'],  # Only use cookies
            'JWT_COOKIE_SECURE': app.config['JWT_COOKIE_SECURE'],
            'JWT_COOKIE_CSRF_PROTECT': app.config['JWT_COOKIE_CSRF_PROTECT'],
            'JWT_CSRF_CHECK_FORM': True,
            'JWT_ACCESS_COOKIE_NAME': 'access_token_cookie',
            'JWT_REFRESH_COOKIE_NAME': 'refresh_token',
            'JWT_ACCESS_COOKIE_PATH': '/',
            'JWT_REFRESH_COOKIE_PATH': refresh_path,
            'JWT_COOKIE_SAMESITE': 'Lax' if app.debug else 'Strict'
        })

        self.jwt.init_app(app)
        self._register_callbacks()

    def _register_callbacks(self):
        """Register all JWT callbacks."""

        @self.jwt.additional_claims_loader
        def add_claims_to_access_token(user):
            """
            Handle both dictionary and string inputs for backwards compatibility
            """
            if isinstance(user, str):
                # If user is a string (just the ID), return minimal claims
                return {
                    'roles': [],
                    'permissions': [],
                    'iat': datetime.utcnow(),
                    'type': 'access'
                }

            # If user is a dictionary, return full claims
            return {
                'roles': user.get('roles', []),
                'permissions': user.get('permissions', []),
                'email': user.get('email'),
                'iat': datetime.utcnow(),
                'type': 'access'
            }

        @self.jwt.user_identity_loader
        def user_identity_lookup(user):
            """Handle both dictionary and string inputs"""
            if isinstance(user, str):
                return user
            return str(user['id'])

    def create_tokens(self, user: Dict[str, Any], fresh: bool = False) -> Dict[str, str]:
        """Create access and refresh tokens for user."""
        try:
            # Ensure default permissions are included
            default_permissions = [
                'profile:read',
                'profile:update',
                'auth:logout',
                'auth:refresh',
                'pipeline:list',
                'pipeline:read',
                'pipeline:create',
                'data_sources:upload_file',  # Add this permission
                'data_sources:list',  # You might want these too
                'data_sources:read'  # for full functionality
            ]

            # Combine user permissions with defaults
            user_permissions = set(user.get('permissions', []) + default_permissions)

            # Create access token claims
            access_claims = {
                'roles': user.get('roles', []),
                'permissions': list(user_permissions),  # Convert set back to list
                'email': user.get('email'),
                'type': 'access',
                'iat': datetime.utcnow()
            }

            access_token = create_access_token(
                identity=str(user['id']),
                additional_claims=access_claims,
                fresh=fresh,
                expires_delta=timedelta(seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES'])
            )

            # Create refresh token with minimal claims
            refresh_claims = {
                'type': 'refresh',
                'iat': datetime.utcnow()
            }

            refresh_token = create_refresh_token(
                identity=str(user['id']),
                additional_claims=refresh_claims,
                expires_delta=timedelta(seconds=current_app.config['JWT_REFRESH_TOKEN_EXPIRES'])
            )

            return {
                'access_token': access_token,
                'refresh_token': refresh_token
            }

        except Exception as e:
            logger.error(f"Error creating tokens: {str(e)}")
            raise

    def blacklist_token(self, jti: str) -> None:
        """Add token to blacklist."""
        self.blacklisted_tokens.add(jti)

    def verify_permission(self, required_permission: str) -> bool:
        """Verify if current user has required permission."""
        try:
            claims = get_jwt()
            user_permissions = claims.get('permissions', [])
            return required_permission in user_permissions
        except Exception as e:
            logger.error(f"Error verifying permission: {str(e)}")
            return False

    @staticmethod
    def permission_required(permission: str) -> Callable:
        """Decorator for permission-based authorization."""

        def decorator(fn: Callable) -> Callable:
            @wraps(fn)
            def wrapper(*args, **kwargs):
                try:
                    verify_jwt_in_request()
                    claims = get_jwt()
                    user_permissions = claims.get('permissions', [])

                    if permission not in user_permissions:
                        return jsonify({
                            'message': 'Insufficient permissions',
                            'error': 'permission_denied',
                            'required_permission': permission
                        }), 403

                    return fn(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Permission verification error: {str(e)}")
                    return jsonify({
                        'message': 'Authorization failed',
                        'error': 'authorization_error'
                    }), 401

            return wrapper

        return decorator

    def get_token(self) -> Optional[str]:
        """Extract access token from request cookies."""
        return request.cookies.get(current_app.config['JWT_ACCESS_COOKIE_NAME'])

    def get_refresh_token(self) -> Optional[str]:
        """Extract refresh token from request cookies."""
        return request.cookies.get(current_app.config['JWT_REFRESH_COOKIE_NAME'])

    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode token."""
        try:
            return self.jwt.decode_token(token)
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            raise

    @staticmethod
    def role_required(roles: list) -> Callable:
        """Decorator for role-based authorization."""

        def decorator(fn: Callable) -> Callable:
            @wraps(fn)
            def wrapper(*args, **kwargs):
                try:
                    verify_jwt_in_request()
                    claims = get_jwt()
                    user_roles = claims.get('roles', [])

                    if not set(roles).intersection(set(user_roles)):
                        return jsonify({
                            'message': 'Insufficient roles',
                            'error': 'role_denied',
                            'required_roles': roles
                        }), 403

                    return fn(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Role verification error: {str(e)}")
                    return jsonify({
                        'message': 'Authorization failed',
                        'error': 'authorization_error'
                    }), 401

            return wrapper

        return decorator