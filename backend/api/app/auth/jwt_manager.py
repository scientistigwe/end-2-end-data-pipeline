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
        
        @self.jwt.user_claims_loader
        def add_claims_to_access_token(user: Dict[str, Any]) -> Dict[str, Any]:
            return {
                'roles': user.get('roles', []),
                'permissions': user.get('permissions', []),
                'email': user.get('email'),
                'iat': datetime.utcnow(),
                'type': 'access'
            }

        @self.jwt.user_identity_loader
        def user_identity_lookup(user: Dict[str, Any]) -> str:
            return str(user['id'])

        @self.jwt.token_verification_loader
        def verify_token(_jwt_header, jwt_data):
            try:
                token_type = jwt_data["type"]
                return token_type in ["access", "refresh"]
            except KeyError:
                return False

        @self.jwt.token_in_blocklist_loader
        def check_if_token_revoked(_jwt_header, jwt_data):
            jti = jwt_data["jti"]
            return jti in self.blacklisted_tokens

        @self.jwt.expired_token_loader
        def expired_token_callback(_jwt_header, _jwt_data):
            return jsonify({
                'message': 'Token has expired',
                'error': 'token_expired'
            }), 401

        @self.jwt.invalid_token_loader
        def invalid_token_callback(error):
            return jsonify({
                'message': 'Invalid token',
                'error': 'invalid_token',
                'details': str(error)
            }), 401

        @self.jwt.unauthorized_loader
        def missing_token_callback(error):
            return jsonify({
                'message': 'Authorization token is missing',
                'error': 'authorization_required',
                'details': str(error)
            }), 401

        @self.jwt.needs_fresh_token_loader
        def token_not_fresh_callback(_jwt_header, _jwt_data):
            return jsonify({
                'message': 'Fresh token required',
                'error': 'fresh_token_required'
            }), 401

    def create_tokens(self, user: Dict[str, Any], fresh: bool = False) -> Dict[str, str]:
        """Create access and refresh tokens for user."""
        try:
            access_token = create_access_token(
                identity=str(user['id']),  # Ensure we're using string ID
                fresh=fresh,
                expires_delta=current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
            )
            
            refresh_token = create_refresh_token(
                identity=str(user['id']),  # Ensure we're using string ID
                expires_delta=current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
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