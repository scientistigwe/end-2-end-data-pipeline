# api/fastapi_app/middleware/auth_middleware.py

import os
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from jose import JWTError, jwt
from core.services.auth.auth_service import AuthService
from ..dependencies.database import get_db_session
from ..utils.route_registry import APIRoutes, RouteDefinition

logger = logging.getLogger(__name__)
security = HTTPBearer()


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


class AuthMiddleware:
    """Authentication middleware for FastAPI"""

    def __init__(self):
        self.security = HTTPBearer()

    def __init__(self):
        self.security = HTTPBearer()
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")

        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY must be set in environment variables")

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
            credentials: HTTPAuthorizationCredentials = Security(security),
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


# Create middleware instance
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

