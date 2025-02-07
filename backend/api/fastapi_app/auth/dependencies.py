# backend/api/fastapi_app/auth/dependencies.py

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from core.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models.auth.user import User  # Adjust import based on your project structure

from jose import jwt, JWTError
from config.app_config import config

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Dependency to get the current authenticated user

    Args:
        token: JWT token from Authorization header
        db: Database session

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        # Decode the JWT token
        payload = jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Fetch user from database
    query = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = query.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


async def get_optional_user(
        token: Optional[str] = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """
    Dependency to get the current user if authenticated,
    or None if no valid token is provided

    Args:
        token: Optional JWT token from Authorization header
        db: Database session

    Returns:
        Authenticated User object or None
    """
    if not token:
        return None

    try:
        # Decode the JWT token
        payload = jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")

        if user_id is None:
            return None

    except JWTError:
        return None

    # Fetch user from database
    query = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = query.scalar_one_or_none()

    return user