# app/auth/jwt_manager.py
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

logger = logging.getLogger(__name__)

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
        app.config['JWT_SECRET_KEY'] = app.config['SECRET_KEY']
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
        app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
        app.config['JWT_ERROR_MESSAGE_KEY'] = 'message'
        app.config['JWT_TOKEN_LOCATION'] = ['headers']
        app.config['JWT_HEADER_NAME'] = 'Authorization'
        app.config['JWT_HEADER_TYPE'] = 'Bearer'

        self.jwt.init_app(app)

        # Register JWT callbacks
        @self.jwt.user_claims_loader
        def add_claims_to_access_token(user: Dict[str, Any]) -> Dict[str, Any]:
            """Add custom claims to JWT token."""
            return {
                'roles': user.get('roles', []),
                'permissions': user.get('permissions', []),
                'email': user.get('email'),
                'iat': datetime.utcnow(),
                'type': 'access'
            }

        @self.jwt.user_identity_loader
        def user_identity_lookup(user: Dict[str, Any]) -> str:
            """Extract user identity for JWT token."""
            return str(user['id'])

        @self.jwt.token_verification_loader
        def verify_token(_jwt_header, jwt_data):
            """Additional token verification."""
            try:
                token_type = jwt_data["type"]
                return token_type in ["access", "refresh"]
            except KeyError:
                return False

        @self.jwt.token_in_blocklist_loader
        def check_if_token_revoked(_jwt_header, jwt_data):
            """Check if token is revoked."""
            jti = jwt_data["jti"]
            return jti in self.blacklisted_tokens

        @self.jwt.expired_token_loader
        def expired_token_callback(_jwt_header, _jwt_data):
            """Handle expired token."""
            return jsonify({
                'message': 'Token has expired',
                'error': 'token_expired'
            }), 401

        @self.jwt.invalid_token_loader
        def invalid_token_callback(error):
            """Handle invalid token."""
            return jsonify({
                'message': 'Invalid token',
                'error': 'invalid_token',
                'details': str(error)
            }), 401

        @self.jwt.unauthorized_loader
        def missing_token_callback(error):
            """Handle missing token."""
            return jsonify({
                'message': 'Authorization token is missing',
                'error': 'authorization_required',
                'details': str(error)
            }), 401

        @self.jwt.needs_fresh_token_loader
        def token_not_fresh_callback(_jwt_header, _jwt_data):
            """Handle non-fresh token."""
            return jsonify({
                'message': 'Fresh token required',
                'error': 'fresh_token_required'
            }), 401

    def create_tokens(self, user: Dict[str, Any], fresh: bool = False) -> Dict[str, str]:
        """Create access and refresh tokens for user.
        
        Args:
            user: User information dictionary
            fresh: Whether to create a fresh access token
            
        Returns:
            Dictionary containing access and refresh tokens
        """
        try:
            access_token = create_access_token(
                identity=user,
                fresh=fresh,
                additional_claims={'type': 'access'}
            )
            
            refresh_token = create_refresh_token(
                identity=user,
                additional_claims={'type': 'refresh'}
            )

            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer'
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
        """Decorator for permission-based authorization.
        
        Args:
            permission: Required permission string
            
        Returns:
            Decorated function
        """
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

    def get_token_from_request(self) -> Optional[str]:
        """Extract token from request headers."""
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split('Bearer ')[1]
        return None

    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token claims
        
        Raises:
            Exception: If token is invalid
        """
        try:
            return self.jwt.decode_token(token)
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            raise