from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import (
    Column, String, DateTime, Boolean, Enum, ForeignKey,
    CheckConstraint, Index, Integer, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from ..core.base import BaseModel


class User(BaseModel):
    """Core user model for authentication and authorization."""
    __tablename__ = 'users'

    # Authentication fields
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    status = Column(
        Enum('active', 'inactive', 'suspended', 'pending', name='user_status'),
        default='active',
        nullable=False
    )
    role = Column(
        Enum('admin', 'user', 'analyst', 'viewer', name='user_role'),
        default='user',
        nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)

    # Security and verification
    last_login = Column(DateTime)
    email_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), unique=True)
    verification_sent_at = Column(DateTime)
    verification_token_expires_at = Column(DateTime)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)

    # Profile information
    profile_image = Column(String(255))
    phone_number = Column(String(50))
    department = Column(String(100))
    timezone = Column(String(50))
    locale = Column(String(10))
    preferences = Column(JSONB)

    # MFA configuration
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255))
    mfa_backup_codes = Column(JSONB)
    mfa_type = Column(
        Enum('totp', 'sms', 'email', name='mfa_type'),
        nullable=True
    )

    # Relationships
    sessions = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    activity_logs = relationship(
        "UserActivityLog",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    reset_tokens = relationship(
        'PasswordResetToken',
        back_populates='user',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('ix_users_email_status', 'email', 'status'),
        Index('ix_users_role', 'role'),
        Index('ix_users_active', 'is_active'),
        CheckConstraint('failed_login_attempts >= 0', name='ck_valid_login_attempts')
    )

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    @validates('email')
    def validate_email(self, key: str, email: str) -> str:
        """Validate email format."""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")
        return email.lower().strip()

    def check_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def can_login(self) -> bool:
        """Check if user can currently login."""
        return (
            self.is_active and
            self.status == 'active' and
            (not self.locked_until or self.locked_until < datetime.utcnow())
        )

    def increment_failed_attempts(self) -> None:
        """Handle failed login attempt."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)

    def reset_failed_attempts(self) -> None:
        """Reset failed login counter."""
        self.failed_login_attempts = 0
        self.locked_until = None


class UserActivityLog(BaseModel):
    """Model for tracking user activity."""
    __tablename__ = 'user_activity_logs'

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        index=True
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey('user_sessions.id', ondelete='SET NULL')
    )
    activity_type = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    action = Column(String(50), nullable=False)
    details = Column(JSONB)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    success = Column(Boolean, default=True)
    error_details = Column(JSONB)

    # Relationships
    user = relationship("User", back_populates="activity_logs")
    session = relationship("UserSession", back_populates="activity_logs")

    __table_args__ = (
        Index('ix_user_activity_logs_type', 'activity_type'),
        Index('ix_user_activity_logs_entity', 'entity_type', 'entity_id'),
        Index('ix_user_activity_logs_success', 'success')
    )


class PasswordResetToken(BaseModel):
    """Model for password reset tokens."""
    __tablename__ = 'password_reset_tokens'

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    used_at = Column(DateTime)
    created_by_ip = Column(String(45))

    # Relationships
    user = relationship('User', back_populates='reset_tokens')

    __table_args__ = (
        Index('ix_password_reset_tokens_user', 'user_id'),
        CheckConstraint(
            'expires_at > created_at',
            name='ck_token_expiry_valid'
        )
    )


class ServiceAccount(BaseModel):
    """Model for service account credentials."""
    __tablename__ = 'service_accounts'

    name = Column(String(255), nullable=False)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    scope = Column(JSONB, nullable=False, default=list)
    expires_at = Column(DateTime)
    status = Column(
        Enum('active', 'inactive', 'expired', name='service_account_status'),
        default='active',
        nullable=False
    )
    last_used = Column(DateTime)
    api_key_hash = Column(String(255))
    restrictions = Column(JSONB)

    # Relationship to user who created/owns the service account
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index('ix_service_accounts_status', 'status'),
        Index('ix_service_accounts_name', 'name'),
        CheckConstraint(
            'expires_at IS NULL OR expires_at > created_at',
            name='ck_valid_expiry'
        )
    )

    def is_active(self) -> bool:
        """Check if service account is currently active."""
        now = datetime.utcnow()
        return (
            self.status == 'active' and
            (self.expires_at is None or self.expires_at > now)
        )

    def has_permission(self, permission_scope: str) -> bool:
        """Check if service account has specific permission."""
        return (
            self.is_active() and
            any(permission_scope in scope for scope in self.scope)
        )