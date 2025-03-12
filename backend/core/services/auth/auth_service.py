# backend/api/fastapi_app/pipeline/auth/auth_service.py

import logging
import os
from jose import jwt
import secrets
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from datetime import datetime, timedelta
from passlib.context import CryptContext

from db.models.auth import User, UserSession, PasswordResetToken

# Configure password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def _hash_password(self, password: str) -> str:
        """Hash a password using passlib."""
        return pwd_context.hash(password)

    async def create_tokens(self, user_data):
        """Create access and refresh tokens for a user"""
        try:
            # Get settings from config or environment
            secret_key = os.environ.get("JWT_SECRET_KEY")
            algorithm = os.environ.get("JWT_ALGORITHM", "HS256")
            access_token_expiry = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 3600))
            refresh_token_expiry = int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", 2592000))

            # Create token expiry times
            access_token_expires = datetime.utcnow() + timedelta(seconds=access_token_expiry)
            refresh_token_expires = datetime.utcnow() + timedelta(seconds=refresh_token_expiry)

            # Create access token
            access_token_payload = {
                "sub": user_data["id"],
                "exp": access_token_expires,
                "type": "access",
                "roles": user_data.get("roles", []),
                "permissions": user_data.get("permissions", [])
            }

            # Create refresh token
            refresh_token_payload = {
                "sub": user_data["id"],
                "exp": refresh_token_expires,
                "type": "refresh"
            }

            # Encode tokens
            access_token = jwt.encode(
                access_token_payload,
                secret_key,
                algorithm=algorithm
            )

            refresh_token = jwt.encode(
                refresh_token_payload,
                secret_key,
                algorithm=algorithm
            )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": access_token_expiry
            }

        except Exception as e:
            self.logger.error(f"Error creating tokens: {str(e)}")
            raise

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash using passlib."""
        return pwd_context.verify(plain_password, hashed_password)

    async def register_user(self, data: Dict[str, Any]) -> User:
        """Register a new user."""
        try:
            # Check if user exists
            existing_user = await self.get_user_by_email(data['email'])
            if existing_user:
                raise ValueError("Email already registered")

            password_hash = self._hash_password(data['password'])

            # Create user with required fields
            user = User(
                email=data['email'],
                password_hash=password_hash,
                first_name=data['first_name'],
                last_name=data['last_name'],
                username=data['username'],
                role='user',
                status='active',
                is_active=True
            )

            # Add optional fields if provided
            optional_fields = [
                'phone_number', 'department',
                'timezone', 'locale', 'preferences'
            ]

            for field in optional_fields:
                if field in data and data[field] is not None:
                    setattr(user, field, data[field])

            self.db_session.add(user)
            await self.db_session.commit()
            await self.db_session.refresh(user)
            return user
        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(f"User registration error: {str(e)}")
            raise

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user."""
        try:
            user = await self.get_user_by_email(email)
            if not user:
                return None

            if not user.is_active:
                raise ValueError("Account is inactive")

            if user.failed_login_attempts >= 5 and user.locked_until and user.locked_until > datetime.utcnow():
                raise ValueError("Account is locked. Please try again later")

            if not self._verify_password(password, user.password_hash):
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                await self.db_session.commit()
                return None

            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            await self.db_session.commit()
            return user

        except ValueError as e:
            raise
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            raise

    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> None:
        """Change user's password after verifying current password."""
        try:
            query = select(User).filter_by(id=user_id)
            result = await self.db_session.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError("User not found")

            if not self._verify_password(current_password, user.password_hash):
                raise ValueError("Invalid current password")

            # Update password
            user.password_hash = self._hash_password(new_password)
            await self.db_session.commit()

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(f"Password change error: {str(e)}")
            raise

    async def reset_password(self, token: str, new_password: str) -> User:
        """Reset user's password using reset token."""
        try:
            query = select(PasswordResetToken).filter_by(token=token)
            result = await self.db_session.execute(query)
            reset_record = result.scalar_one_or_none()

            if not reset_record:
                raise ValueError("Invalid reset token")

            if reset_record.expires_at < datetime.utcnow():
                raise ValueError("Reset token has expired")

            query = select(User).filter_by(id=reset_record.user_id)
            result = await self.db_session.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError("User not found")

            # Update password
            user.password_hash = self._hash_password(new_password)

            # Delete the used reset token
            await self.db_session.delete(reset_record)
            await self.db_session.commit()

            return user

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(f"Password reset error: {str(e)}")
            raise

    async def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        try:
            user = await self.get_user_by_id(user_id)
            if user:
                user.last_login = datetime.utcnow()
                await self.db_session.commit()
        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(f"Error updating last login: {str(e)}")
            raise

    async def create_session(self, user_id: UUID, device_info: Dict = None) -> UserSession:
        """Create a new user session."""
        try:
            session = UserSession(
                user_id=user_id,
                expires_at=datetime.utcnow() + timedelta(days=1),
                device_id=device_info.get('device_id') if device_info else None,
                device_type=device_info.get('device_type') if device_info else None,
                ip_address=device_info.get('ip_address') if device_info else None,
                user_agent=device_info.get('user_agent') if device_info else None
            )
            self.db_session.add(session)
            await self.db_session.commit()
            await self.db_session.refresh(session)
            return session
        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(f"Session creation error: {str(e)}")
            raise

    async def update_user_profile(self, user_id: UUID, data: Dict[str, Any]) -> User:
        """Update user's profile information."""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")

            # Update allowed fields
            allowed_fields = {
                'first_name', 'last_name', 'phone_number',
                'department', 'timezone', 'locale', 'preferences',
                'profile_image'
            }

            for key, value in data.items():
                if key in allowed_fields:
                    setattr(user, key, value)

            user.updated_at = datetime.utcnow()
            await self.db_session.commit()
            await self.db_session.refresh(user)
            return user
        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(f"Profile update error: {str(e)}")
            raise

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by their ID."""
        try:
            query = select(User).filter_by(id=user_id)
            result = await self.db_session.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                self.logger.warning(f"User not found with id: {user_id}")
                return None
            return user
        except Exception as e:
            self.logger.error(f"Error fetching user by id: {str(e)}")
            raise

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by their email address."""
        try:
            query = select(User).filter_by(email=email)
            result = await self.db_session.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                self.logger.warning(f"User not found with email: {email}")
                return None
            return user
        except Exception as e:
            self.logger.error(f"Error fetching user by email: {str(e)}")
            raise

    async def invalidate_token(self, token_jti: str) -> None:
        """Invalidate a JWT token."""
        try:
            session = UserSession(
                token=token_jti,
                expires_at=datetime.utcnow()
            )
            self.db_session.add(session)
            await self.db_session.commit()
        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(f"Token invalidation error: {str(e)}")
            raise

    async def verify_email(self, token: str) -> User:
        """
        Verify user's email address.

        Args:
            token (str): Email verification token

        Returns:
            User: Verified user

        Raises:
            ValueError: If token is invalid or expired
        """
        try:
            # Find user with the verification token
            query = select(User).filter_by(verification_token=token)
            result = await self.db_session.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError("Invalid verification token")

            # Check token expiration (e.g., token valid for 24 hours)
            if user.verification_token_expires_at < datetime.utcnow():
                raise ValueError("Verification token has expired")

            # Mark user as verified
            user.is_verified = True
            user.verified_at = datetime.utcnow()
            user.verification_token = None
            user.verification_token_expires_at = None

            await self.db_session.commit()
            return user

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(f"Email verification error: {str(e)}")
            raise

    async def generate_verification_token(self, user: User) -> str:
        """
        Generate email verification token for a user.

        Args:
            user (User): User to generate token for

        Returns:
            str: Verification token
        """
        try:
            # Generate a secure random token
            token = secrets.token_urlsafe(32)

            # Set token expiration to 24 hours from now
            user.verification_token = token
            user.verification_token_expires_at = datetime.utcnow() + timedelta(hours=24)

            await self.db_session.commit()
            return token

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(f"Token generation error: {str(e)}")
            raise

    async def initiate_password_reset(self, email: str) -> str:
        """
        Initiate password reset process.

        Args:
            email (str): User's email address

        Returns:
            str: Password reset token

        Raises:
            ValueError: If user not found
        """
        try:
            # Find user by email
            query = select(User).filter_by(email=email)
            result = await self.db_session.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError("User not found")

            # Generate a secure password reset token
            reset_token = secrets.token_urlsafe(32)

            # Create or update password reset token record
            reset_record = PasswordResetToken(
                user_id=user.id,
                token=reset_token,
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )

            self.db_session.add(reset_record)
            await self.db_session.commit()

            return reset_token

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(f"Password reset initiation error: {str(e)}")
            raise

    async def verify_account(self, token: str) -> User:
        """
        Verify user's account using verification token.

        Args:
            token (str): Verification token

        Returns:
            User: Verified user object

        Raises:
            ValueError: If token is invalid or expired
        """
        try:
            # Use email verification method
            return await self.verify_email(token)

        except Exception as e:
            self.logger.error(f"Account verification error: {str(e)}")
            raise

    def get_user_permissions(self, user) -> list:
        """
        Get user permissions based on role.

        Args:
            user (User): User object

        Returns:
            list: Sorted list of user permissions
        """
        # Define base permissions that all users have
        base_permissions = ['read:own_profile', 'update:own_profile']

        # Role-based permissions
        role_permissions = {
            'admin': [
                'read:all_users',
                'create:users',
                'update:users',
                'delete:users',
                'read:system_settings',
                'update:system_settings',
                'manage:pipelines',
                'manage:data_sources'
            ],
            'user': [
                'read:own_data',
                'create:own_pipelines',
                'update:own_pipelines'
            ],
            'analyst': [
                'read:analytics',
                'create:reports',
                'read:all_pipelines'
            ],
            'viewer': [
                'read:public_data',
                'read:public_pipelines'
            ]
        }

        # Get role-specific permissions
        user_role = getattr(user, 'role', 'viewer')  # Default to viewer if role not set
        permissions = base_permissions + role_permissions.get(user_role, [])

        return sorted(list(set(permissions)))  # Remove duplicates and sort


    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using a valid refresh token.

        Args:
            refresh_token (str): The refresh token provided by the user

        Returns:
            Dict[str, Any]: New tokens including access_token and refresh_token

        Raises:
            ValueError: If token is invalid, expired, or user not found
        """
        try:
            # Get settings from config
            secret_key = os.environ.get("JWT_SECRET_KEY")
            algorithm = os.environ.get("JWT_ALGORITHM", "HS256")

            # Decode and validate the refresh token
            try:
                payload = jwt.decode(
                    refresh_token,
                    secret_key,
                    algorithms=[algorithm]
                )

                # Verify this is a refresh token
                if payload.get("type") != "refresh":
                    raise ValueError("Invalid token type")

                user_id = payload.get("sub")
                if not user_id:
                    raise ValueError("Invalid token: missing user ID")

            except Exception as e:
                self.logger.error(f"JWT decode error: {str(e)}")
                raise ValueError("Invalid or expired token")

            # Get the user
            user = await self.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")

            if not user.is_active:
                raise ValueError("User account is inactive")

            # Create user data for token generation
            user_data = {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "roles": [user.role],
                "permissions": self.get_user_permissions(user)
            }

            # Generate new tokens
            return await self.create_tokens(user_data)

        except ValueError as e:
            self.logger.error(f"Token refresh error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in token refresh: {str(e)}")
            raise ValueError("Error processing token refresh")