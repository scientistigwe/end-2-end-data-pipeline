from typing import Optional, Annotated
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import JWTError, jwt
from pydantic import BaseModel
from datetime import datetime

from config.settings import settings
from db.models.auth import User


class TokenData(BaseModel):
    username: Optional[str] = None
    roles: list[str] = []


# OAuth2 scheme for JWT tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# API Key scheme
api_key_header = APIKeyHeader(name="X-API-Key")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """
    Dependency to get the current authenticated user.

    Args:
        token: JWT token from request

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        token_data = TokenData(
            username=username,
            roles=payload.get("roles", [])
        )
    except JWTError:
        raise credentials_exception

    # Get user from database using username
    # This is a placeholder - implement your user retrieval logic
    user = await get_user_from_db(username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
        current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency to get current active user.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        User: Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def check_role(required_role: str):
    """
    Create a dependency that checks for a specific role.

    Args:
        required_role: Role to check for

    Returns:
        Dependency function checking for role
    """

    async def role_checker(
            current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        if required_role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user

    return role_checker


# Role-specific dependencies
get_admin_user = check_role("admin")


async def verify_api_key(
        api_key: Annotated[str, Security(api_key_header)]
) -> str:
    """
    Dependency to verify API key.

    Args:
        api_key: API key from request header

    Returns:
        str: Verified API key

    Raises:
        HTTPException: If API key is invalid
    """
    if api_key not in settings.API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    return api_key


# Example usage in routes:
"""
@router.get("/users/me")
async def read_user_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return current_user

@router.get("/admin/users")
async def read_all_users(
    current_user: Annotated[User, Depends(get_admin_user)]
):
    # Only admins can access this
    return {"message": "Admin only endpoint"}

@router.get("/service/status")
async def check_service_status(
    api_key: Annotated[str, Depends(verify_api_key)]
):
    return {"status": "operational"}
"""