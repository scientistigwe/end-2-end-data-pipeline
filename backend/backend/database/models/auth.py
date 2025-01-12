from sqlalchemy import (
   Column, String, DateTime, Boolean, Enum, ForeignKey, Text,
   CheckConstraint, Index, UniqueConstraint, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from .base import BaseModel
from datetime import datetime, timedelta

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .events import EventSubscription

class User(BaseModel):
    """User model for authentication and authorization."""
    __tablename__ = 'users'

    # Authentication fields
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    status = Column(
        Enum('active', 'inactive', 'suspended', name='user_status'),
        default='active',
        nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    role = Column(
        Enum('admin', 'user', 'analyst', 'viewer', name='user_role'),
        default='user',
        nullable=False
    )

    # Account details
    last_login = Column(DateTime)
    email_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), unique=True)
    verification_sent_at = Column(DateTime)
    password_reset_token = Column(String(255), unique=True)
    password_reset_expires = Column(DateTime)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
   
    # Profile
    profile_image = Column(String(255))
    phone_number = Column(String(50))
    department = Column(String(100))
    timezone = Column(String(50))
    locale = Column(String(10))
    preferences = Column(JSONB)

    # Relationships
    sessions = relationship(
        "UserSession",
        back_populates="user",
        foreign_keys="UserSession.user_id",
        cascade="all, delete-orphan"
    )
    data_sources = relationship(
        "DataSource",
        back_populates="owner",
        foreign_keys="[DataSource.owner_id]"
    )
    pipelines = relationship(
        "Pipeline",
        back_populates="owner",
        foreign_keys="[Pipeline.owner_id]"
    )
    activity_logs = relationship(
        "UserActivityLog",
        back_populates="user",
        foreign_keys="UserActivityLog.user_id",
        cascade="all, delete-orphan"
    )
    decision_history = relationship(
        "DecisionHistory",
        back_populates="user",
        foreign_keys="[DecisionHistory.user_id]"
    )
    recommendation_feedback = relationship(
        "RecommendationFeedback",
        back_populates="user",
        foreign_keys="[RecommendationFeedback.user_id]"
    )
    settings = relationship(
        'UserSettings',
        back_populates='user',
        foreign_keys='[UserSettings.user_id]',
        uselist=False  # One-to-one relationship
    )
    modified_system_settings = relationship(
        'SystemSettings',
        foreign_keys='[SystemSettings.last_modified_by]',
        back_populates='modifier'
    )
    notifications = relationship(
        'Notification',
        back_populates='user',
        foreign_keys='[Notification.user_id]',
        cascade='all, delete-orphan'
    )
    # Modify the event_subscriptions relationship
    event_subscriptions = relationship(
        'EventSubscription',  # Use string reference
        back_populates='user',
        foreign_keys='[EventSubscription.user_id]',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('ix_users_email_status', 'email', 'status'),
        Index('ix_users_role', 'role'),
        Index('ix_users_active', 'is_active'),  # Added index for is_active
        CheckConstraint(
            'password_reset_expires > verification_sent_at',
            name='ck_valid_reset_expiry'
        ),
        CheckConstraint(
            'failed_login_attempts >= 0',
            name='ck_valid_login_attempts'
        )
    )

    @property
    def full_name(self) -> str:
        """Get full name by combining first and last name."""
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    @validates('email')
    def validate_email(self, key: str, email: str) -> str:
        """Validate email format."""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")
        return email.lower().strip()

    @validates('first_name', 'last_name')
    def validate_name(self, key: str, name: str) -> str:
        """Validate name fields."""
        if name:
            return name.strip()
        return name

    def check_password(self, password: str) -> bool:
        """Check if provided password matches stored hash."""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def can_login(self) -> bool:
        """Check if user can login."""
        return (
            self.is_active and
            self.status == 'active' and
            (not self.locked_until or self.locked_until < datetime.utcnow())
        )

    def increment_failed_attempts(self) -> None:
        """Increment failed login attempts and handle account locking."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:  # Configure max attempts as needed
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)  # Lock for 30 minutes

    def reset_failed_attempts(self) -> None:
        """Reset failed login attempts counter."""
        self.failed_login_attempts = 0
        self.locked_until = None

    def __repr__(self) -> str:
        return f"<User(email='{self.email}', full_name='{self.full_name}', role='{self.role}')>"


class UserSession(BaseModel):
    """Model for tracking user sessions."""
    __tablename__ = 'user_sessions'

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    token = Column(String(255), unique=True, nullable=False)
    refresh_token = Column(String(255), unique=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime)
    revocation_reason = Column(String(255))
   
    # Device info
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    device_id = Column(String(255))
    device_type = Column(String(50))
    location = Column(JSONB)

    # Activity tracking 
    last_activity = Column(DateTime)
    access_count = Column(Integer, default=0)
    security_events = Column(JSONB)

    # Relationships
    user = relationship(
        "User",
        back_populates="sessions",
        foreign_keys=[user_id]
    )
    activity_logs = relationship(
        "UserActivityLog",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_user_sessions_token', 'token'),
        Index('ix_user_sessions_expires', 'expires_at'),
        CheckConstraint(
            'expires_at > created_at',
            name='ck_valid_session_expiry'
        ),
        CheckConstraint(
            'revoked_at IS NULL OR revoked_at <= expires_at',
            name='ck_valid_revocation_time'
        ),
        CheckConstraint(
            'access_count >= 0',
            name='ck_valid_access_count'
        )
    )

    @validates('expires_at')
    def validate_expiry(self, key, expires_at):
        """Validate session expiry time."""
        if expires_at <= datetime.utcnow():
            raise ValueError("Session expiry must be in the future")
        return expires_at

    def is_active(self):
        """Check if session is currently active."""
        now = datetime.utcnow()
        return (
            not self.revoked and
            self.expires_at > now and
            (not self.last_activity or 
             self.last_activity > now - timedelta(hours=24))
        )

    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, active={self.is_active()})>"


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
    user = relationship(
        "User", 
        back_populates="activity_logs",
        foreign_keys=[user_id]
    )
    session = relationship(
        "UserSession",
        back_populates="activity_logs",
        foreign_keys=[session_id]
    )

    __table_args__ = (
        Index('ix_user_activity_logs_type', 'activity_type'),
        Index('ix_user_activity_logs_entity', 'entity_type', 'entity_id'),
        Index('ix_user_activity_logs_success', 'success'),
        {'extend_existing': True}
    )