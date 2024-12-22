# backend/flask_api/app/services/auth/auth_service.py
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from backend.database.models.auth import User, UserSession
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def register_user(self, data: Dict[str, Any]) -> User:
        """Register a new user."""
        try:
            password_hash = generate_password_hash(data['password'])
            user = User(
                email=data['email'],
                password_hash=password_hash,
                full_name=data.get('full_name'),
                role='user'
            )
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
            user = self.db_session.query(User).filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                return user
            return None
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            raise

    def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        try:
            user = self.db_session.query(User).get(user_id)
            if user:
                user.last_login = datetime.utcnow()
                self.db_session.commit()
        except Exception as e:
            self.logger.error(f"Error updating last login: {str(e)}")
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

    def get_user_profile(self, user_id: UUID) -> User:
        """Get user's profile information."""
        try:
            user = self.db_session.query(User).get(user_id)
            if not user:
                raise ValueError("User not found")
            return user
        except Exception as e:
            self.logger.error(f"Profile fetch error: {str(e)}")
            raise

    def update_user_profile(self, user_id: UUID, data: Dict[str, Any]) -> User:
        """Update user's profile information."""
        try:
            user = self.db_session.query(User).get(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Update fields
            for key, value in data.items():
                if hasattr(user, key) and key != 'password_hash':
                    setattr(user, key, value)
                    
            self.db_session.commit()
            return user
        except Exception as e:
            self.logger.error(f"Profile update error: {str(e)}")
            self.db_session.rollback()
            raise