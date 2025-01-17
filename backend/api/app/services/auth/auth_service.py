# backend/api/app/services/auth/auth_service.py
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from backend.db.models.auth import User, UserSession
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def register_user(self, data: Dict[str, Any]) -> User:
        """Register a new user."""
        try:
            # Check if user exists
            if self.get_user_by_email(data['email']):
                raise ValueError("Email already registered")

            password_hash = generate_password_hash(data['password'])
            
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
            self.db_session.commit()
            return user
        except Exception as e:
            self.logger.error(f"User registration error: {str(e)}")
            self.db_session.rollback()
            raise

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user."""
        try:
            user = self.get_user_by_email(email)
            if not user:
                return None

            if not user.is_active:
                raise ValueError("Account is inactive")

            if user.failed_login_attempts >= 5 and user.locked_until and user.locked_until > datetime.utcnow():
                raise ValueError("Account is locked. Please try again later")

            if not check_password_hash(user.password_hash, password):
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                self.db_session.commit()
                return None

            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            self.db_session.commit()
            return user

        except ValueError as e:
            raise
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            raise

    def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        try:
            user = self.get_user_by_id(user_id)
            if user:
                user.last_login = datetime.utcnow()
                self.db_session.commit()
        except Exception as e:
            self.logger.error(f"Error updating last login: {str(e)}")
            self.db_session.rollback()
            raise

    def create_session(self, user_id: UUID, device_info: Dict = None) -> UserSession:
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
                self.db_session.commit()
                return session
            except Exception as e:
                self.logger.error(f"Session creation error: {str(e)}")
                self.db_session.rollback()
                raise

    def update_user_profile(self, user_id: UUID, data: Dict[str, Any]) -> User:
        """Update user's profile information."""
        try:
            user = self.get_user_by_id(user_id)
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
            self.db_session.commit()
            return user
        except Exception as e:
            self.logger.error(f"Profile update error: {str(e)}")
            self.db_session.rollback()
            raise

    def invalidate_token(self, token_jti: str) -> None:
        """Invalidate a JWT token."""
        try:
            session = UserSession(
                token=token_jti,
                expires_at=datetime.utcnow()
            )
            self.db_session.add(session)
            self.db_session.commit()
        except Exception as e:
            self.logger.error(f"Token invalidation error: {str(e)}")
            self.db_session.rollback()
            raise

    def verify_email(self, token: str) -> None:
        """Verify user's email address."""
        try:
            # Add email verification logic
            pass
        except Exception as e:
            self.logger.error(f"Email verification error: {str(e)}")
            raise

    def initiate_password_reset(self, email: str) -> None:
        """Initiate password reset process."""
        try:
            user = self.db_session.query(User).filter_by(email=email).first()
            if user:
                # Add password reset logic
                pass
        except Exception as e:
            self.logger.error(f"Password reset initiation error: {str(e)}")
            raise

    def reset_password(self, token: str, new_password: str) -> None:
        """Reset user's password using reset token."""
        try:
            # Add password reset logic
            pass
        except Exception as e:
            self.logger.error(f"Password reset error: {str(e)}")
            raise

    def change_password(self, user_id: UUID, current_password: str, new_password: str) -> None:
        """Change user's password."""
        try:
            user = self.db_session.query(User).get(user_id)
            if user and check_password_hash(user.password_hash, current_password):
                user.password_hash = generate_password_hash(new_password)
                self.db_session.commit()
            else:
                raise ValueError("Invalid current password")
        except Exception as e:
            self.logger.error(f"Password change error: {str(e)}")
            self.db_session.rollback()
            raise

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by their ID.
        
        Args:
            user_id (UUID): The user's unique identifier
            
        Returns:
            Optional[User]: The user object if found, None otherwise
            
        Raises:
            Exception: If db query fails
        """
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            if not user:
                self.logger.warning(f"User not found with id: {user_id}")
                return None
            return user
        except Exception as e:
            self.logger.error(f"Error fetching user by id: {str(e)}")
            raise

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by their email address.
        
        Args:
            email (str): The user's email address
            
        Returns:
            Optional[User]: The user object if found, None otherwise
            
        Raises:
            Exception: If db query fails
        """
        try:
            user = self.db_session.query(User).filter_by(email=email).first()
            if not user:
                self.logger.warning(f"User not found with email: {email}")
                return None
            return user
        except Exception as e:
            self.logger.error(f"Error fetching user by email: {str(e)}")
            raise

    def get_user_profile(self, user_id: UUID) -> User:
        """
        Get user's profile information.
        
        Args:
            user_id (UUID): The user's unique identifier
            
        Returns:
            User: The user's profile information
            
        Raises:
            ValueError: If user is not found
            Exception: If db query fails
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                raise ValueError(f"User not found with id: {user_id}")
            return user
        except Exception as e:
            self.logger.error(f"Profile fetch error: {str(e)}")
            raise

    def verify_account(self, token: str) -> User:
        """
        Verify user's account using verification token.
        
        Args:
            token (str): The verification token
            
        Returns:
            User: The verified user object
            
        Raises:
            ValueError: If token is invalid or expired
            Exception: If verification fails
        """
        try:
            # Verify the token and get user_id
            user_id = self.verify_token(token, purpose='account_verification')
            
            user = self.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
                
            # Update user verification status
            user.is_verified = True
            user.verified_at = datetime.utcnow()
            user.verification_token = None
            
            self.db_session.commit()
            return user
            
        except Exception as e:
            self.logger.error(f"Account verification error: {str(e)}")
            self.db_session.rollback()
            raise
        
