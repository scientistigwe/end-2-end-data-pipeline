# api/fastapi_app/middleware/auth_middleware.py

import os
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from fastapi import Request, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from jose import JWTError, jwt
from pydantic_settings import BaseSettings
from functools import lru_cache, wraps
from core.services.auth.auth_service import AuthService
from config.database import get_db_session
from ..utils.route_registry import APIRoutes, RouteDefinition

logger = logging.getLogger(__name__)


class AuthSettings(BaseSettings):
    """Authentication settings from environment variables"""
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES: int = 3600
    JWT_REFRESH_TOKEN_EXPIRES: int = 2592000

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields in the settings


@lru_cache()
def get_auth_settings() -> AuthSettings:
    """Get cached auth settings"""
    try:
        settings = AuthSettings()
        logger.info("Auth settings loaded successfully")
        return settings
    except Exception as e:
        logger.error(f"Failed to load auth settings: {e}")
        raise ValueError("Failed to load authentication settings") from e


class AuthMiddleware:
    """Authentication middleware for FastAPI"""

    def __init__(self):
        try:
            self.security = HTTPBearer()
            self.settings = get_auth_settings()
            self.secret_key = self.settings.JWT_SECRET_KEY
            self.algorithm = self.settings.JWT_ALGORITHM
            logger.info("Auth middleware initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize auth middleware: {e}")
            raise

    async def validate_and_get_user(
            self,
            credentials: HTTPAuthorizationCredentials,
            db: AsyncSession
    ) -> Dict[str, Any]:
        """Validate token and return user"""
        try:
            # Verify JWT token
            token = credentials.credentials
            try:
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.algorithm]
                )
            except JWTError as e:
                logger.error(f"JWT decode error: {str(e)}")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication token"
                )

            # Extract and validate token claims
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=401,
                    detail="Token missing user identifier"
                )

            # Check token expiration
            exp = payload.get("exp")
            if not exp:
                raise HTTPException(
                    status_code=401,
                    detail="Token missing expiration"
                )

            if datetime.utcfromtimestamp(exp) < datetime.utcnow():
                raise HTTPException(
                    status_code=401,
                    detail="Token has expired"
                )

            # Validate token type
            token_type = payload.get("type")
            if not token_type or token_type != "access":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token type"
                )

            # Get user from database
            auth_service = AuthService(db)
            user = await auth_service.get_user_by_id(user_id)

            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="User not found"
                )

            return user

        except JWTError:
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials"
            )
        except Exception as e:
            logger.error(f"Error validating user: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=401,
                detail="Authentication failed"
            )

    async def __call__(
            self,
            request: Request,
            credentials: HTTPAuthorizationCredentials = Security(HTTPBearer()),
            db: AsyncSession = Depends(get_db_session)
    ) -> Optional[Dict[str, Any]]:
        """Middleware implementation"""
        try:
            # Check route authentication requirements
            route_def = get_route_from_request(request.url.path, request.method)
            if not route_def or not route_def.requires_auth:
                return None

            # Validate token and get user
            user = await self.validate_and_get_user(credentials, db)

            # Store user in request state
            request.state.user = user
            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Middleware authentication error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=401,
                detail="Authentication failed"
            )


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


# Create singleton instances
auth_settings = get_auth_settings()
auth_middleware = AuthMiddleware()


# Dependency for protected routes
async def get_current_user(
        user: Dict[str, Any] = Depends(auth_middleware)
) -> Dict[str, Any]:
    """Dependency to get current authenticated user"""
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    return user


# Optional user dependency
async def get_optional_user(
        user: Optional[Dict[str, Any]] = Depends(auth_middleware)
) -> Optional[Dict[str, Any]]:
    """Dependency to get optional authenticated user"""
    return user


# Add PermissionError class
class PermissionError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=403, detail=detail)


def require_permission(permission: str) -> Callable:
    """
    Dependency function to check if user has required permission.

    Args:
        permission (str): Required permission string (e.g., "pipeline:read")

    Returns:
        Callable: Dependency function that validates user permissions
    """

    async def permission_dependency(
            current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        try:
            # Get user permissions from the current user
            user_permissions = current_user.get('permissions', [])

            # Check if user has required permission
            if permission not in user_permissions:
                logger.error(
                    f"Permission denied: User {current_user.get('id')} "
                    f"lacks permission '{permission}'"
                )
                raise PermissionError(
                    f"User lacks required permission: {permission}"
                )

            return current_user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error checking permission '{permission}': {str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail="Error checking permissions"
            )

    return permission_dependency