# backend/api/fastapi_app/auth/jwt_manager.py

# backend/api/fastapi_app/auth/jwt_manager.py

from datetime import timedelta, datetime
from typing import Dict, Any, Optional, Callable, List

import jwt
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from functools import wraps

import logging
from ..utils.route_registry import APIRoutes

logger = logging.getLogger(__name__)


class JWTTokenManager:
    """JWT Token management and authentication."""

    def __init__(
            self,
            secret_key: str,
            access_token_expires: int = 3600,
            refresh_token_expires: int = 86400
    ):
        self.secret_key = secret_key
        self.access_token_expires = access_token_expires
        self.refresh_token_expires = refresh_token_expires
        self.blacklisted_tokens = set()  # Simple in-memory blacklist
        self._default_permissions = [
            'profile:read',
            'profile:update',
            'auth:logout',
            'auth:refresh',
            'pipeline:list',
            'pipeline:read',
            'pipeline:create',
            'data_sources:upload_file',
            'data_sources:list',
            'data_sources:read'
        ]

    def _get_default_permissions(self) -> List[str]:
        """Retrieve the list of default permissions assigned to all users."""
        return self._default_permissions.copy()

    def create_tokens(self, user: Dict[str, Any], fresh: bool = False) -> Dict[str, str]:
        """Create access and refresh tokens with proper permission handling."""
        try:
            # Combine user and default permissions
            user_permissions = set(user.get('permissions', []))
            default_permissions = set(self._get_default_permissions())
            combined_permissions = list(user_permissions.union(default_permissions))

            # Prepare claims for access token
            access_token_payload = {
                'sub': str(user['id']),
                'roles': user.get('roles', []),
                'permissions': combined_permissions,
                'email': user.get('email'),
                'type': 'access',
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(seconds=self.access_token_expires)
            }

            # Prepare claims for refresh token
            refresh_token_payload = {
                'sub': str(user['id']),
                'type': 'refresh',
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(seconds=self.refresh_token_expires)
            }

            # Generate tokens
            access_token = jwt.encode(access_token_payload, self.secret_key, algorithm='HS256')
            refresh_token = jwt.encode(refresh_token_payload, self.secret_key, algorithm='HS256')

            return {
                'access_token': access_token,
                'refresh_token': refresh_token
            }

        except Exception as e:
            logger.error(f"Token creation error: {str(e)}")
            raise

    def blacklist_token(self, jti: str) -> None:
        """Add token to blacklist."""
        self.blacklisted_tokens.add(jti)

    def verify_permission(self, token: str, required_permission: str) -> bool:
        """Verify if token has required permission."""
        try:
            # Decode the token
            decoded_token = self.validate_token(token)

            # Check permissions
            user_permissions = decoded_token.get('permissions', [])
            return required_permission in user_permissions
        except Exception as e:
            logger.error(f"Error verifying permission: {str(e)}")
            return False

    def permission_required(self, permission: str):
        """Decorator for permission-based authorization."""

        def decorator(fn: Callable):
            @wraps(fn)
            async def wrapper(request: Request, *args, **kwargs):
                # Get token from Authorization header
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer '):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail='Invalid or missing token'
                    )

                token = auth_header.split(' ')[1]

                try:
                    # Validate token and check permissions
                    decoded_token = self.validate_token(token)
                    user_permissions = decoded_token.get('permissions', [])

                    if permission not in user_permissions:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail='Insufficient permissions',
                            headers={
                                'WWW-Authenticate': 'Bearer',
                                'X-Required-Permission': permission
                            }
                        )

                    # Add decoded token to request state for potential further use
                    request.state.token = decoded_token
                    return await fn(request, *args, **kwargs)

                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"Permission verification error: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail='Authorization failed'
                    )

            return wrapper

        return decorator

    def role_required(self, roles: List[str]):
        """Decorator for role-based authorization."""

        def decorator(fn: Callable):
            @wraps(fn)
            async def wrapper(request: Request, *args, **kwargs):
                # Get token from Authorization header
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer '):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail='Invalid or missing token'
                    )

                token = auth_header.split(' ')[1]

                try:
                    # Validate token and check roles
                    decoded_token = self.validate_token(token)
                    user_roles = decoded_token.get('roles', [])

                    if not set(roles).intersection(set(user_roles)):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail='Insufficient roles',
                            headers={
                                'WWW-Authenticate': 'Bearer',
                                'X-Required-Roles': ','.join(roles)
                            }
                        )

                    # Add decoded token to request state for potential further use
                    request.state.token = decoded_token
                    return await fn(request, *args, **kwargs)

                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"Role verification error: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail='Authorization failed'
                    )

            return wrapper

        return decorator

    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode token."""
        try:
            # Decode the token
            decoded_token = jwt.decode(
                token,
                self.secret_key,
                algorithms=['HS256']
            )

            # Check if token is blacklisted
            if decoded_token.get('jti') in self.blacklisted_tokens:
                raise ValueError("Token has been blacklisted")

            return decoded_token

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token has expired'
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid token'
            )
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token validation failed'
            )

    def get_token_from_request(self, request: Request) -> Optional[str]:
        """Extract token from Authorization header."""
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
        return None

    def refresh_tokens(self, refresh_token: str) -> Dict[str, str]:
        """
        Refresh access token using a valid refresh token.

        Args:
            refresh_token (str): The refresh token to use for generating new tokens

        Returns:
            Dict[str, str]: A dictionary containing new access and refresh tokens
        """
        try:
            # Validate the refresh token
            decoded_refresh_token = self.validate_token(refresh_token)

            # Ensure this is a refresh token
            if decoded_refresh_token.get('type') != 'refresh':
                raise ValueError("Invalid refresh token")

            # Retrieve user information from the refresh token
            user_id = decoded_refresh_token.get('sub')

            # Fetch user details (you'll need to implement this method to get user info)
            user = self._get_user_by_id(user_id)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='User not found'
                )

            # Create new tokens
            new_tokens = self.create_tokens(user)

            return new_tokens

        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token refresh failed'
            )

    def _get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user information by ID.

        Note: This is a placeholder method. You should replace this with
        actual user retrieval logic from your database or user service.

        Args:
            user_id (str): The ID of the user

        Returns:
            Optional[Dict[str, Any]]: User information or None if not found
        """
        # Placeholder implementation - replace with actual user retrieval
        # This could be a database query, a call to a user service, etc.
        raise NotImplementedError(
            "User retrieval method must be implemented in your specific application. "
            "Override this method with your actual user lookup logic."
        )
