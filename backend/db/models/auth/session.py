from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey, Index,
    CheckConstraint, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from ..core.base import BaseModel


class UserSession(BaseModel):
    """Model for managing user authentication sessions."""
    __tablename__ = 'user_sessions'

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Authentication tokens
    token = Column(String(255), unique=True, nullable=False)
    refresh_token = Column(String(255), unique=True)
    expires_at = Column(DateTime, nullable=False)

    # Session status
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime)
    revocation_reason = Column(String(255))

    # Security tracking
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    device_id = Column(String(255))
    device_type = Column(String(50))
    location = Column(JSONB)
    security_context = Column(JSONB)

    # MFA status
    mfa_verified = Column(Boolean, default=False)
    mfa_verified_at = Column(DateTime)
    mfa_method_used = Column(String(50))

    # Session activity
    last_active = Column(DateTime)
    last_ip = Column(String(45))
    activity_count = Column(Integer, default=0)

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
        Index('ix_user_sessions_device', 'device_id'),
        CheckConstraint(
            'expires_at > created_at',
            name='ck_session_expiry_valid'
        ),
        CheckConstraint(
            'activity_count >= 0',
            name='ck_activity_count_valid'
        )
    )

    def is_active(self) -> bool:
        """Check if session is currently active."""
        now = datetime.utcnow()
        return not self.revoked and self.expires_at > now

    def revoke(self, reason: str = None) -> None:
        """Revoke the session."""
        self.revoked = True
        self.revoked_at = datetime.utcnow()
        self.revocation_reason = reason

    def record_activity(self, ip_address: str = None) -> None:
        """Record session activity."""
        self.last_active = datetime.utcnow()
        if ip_address:
            self.last_ip = ip_address
        self.activity_count += 1


class SessionDevice(BaseModel):
    """Model for tracking user devices used in sessions."""
    __tablename__ = 'session_devices'

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    device_id = Column(String(255), nullable=False)
    device_type = Column(String(50))
    device_name = Column(String(255))

    # Device details
    os_type = Column(String(50))
    os_version = Column(String(50))
    browser_type = Column(String(50))
    browser_version = Column(String(50))

    # Security status
    is_trusted = Column(Boolean, default=False)
    trust_expires_at = Column(DateTime)
    last_used_at = Column(DateTime)
    last_ip = Column(String(45))

    # Risk assessment
    risk_score = Column(Integer, default=0)
    risk_factors = Column(JSONB)
    security_flags = Column(JSONB)

    __table_args__ = (
        Index('ix_session_devices_user_device', 'user_id', 'device_id', unique=True),
        CheckConstraint(
            'risk_score >= 0 AND risk_score <= 100',
            name='ck_risk_score_range'
        )
    )


class RefreshToken(BaseModel):
    """Model for managing refresh tokens."""
    __tablename__ = 'refresh_tokens'

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    token_hash = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Usage tracking
    last_used_at = Column(DateTime)
    use_count = Column(Integer, default=0)
    max_uses = Column(Integer, default=0)

    # Security context
    issued_by_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey('user_sessions.id', ondelete='SET NULL')
    )
    issued_ip = Column(String(45))
    device_id = Column(String(255))

    # Token status
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime)
    revocation_reason = Column(String(255))

    __table_args__ = (
        Index('ix_refresh_tokens_user', 'user_id'),
        CheckConstraint(
            'use_count >= 0',
            name='ck_use_count_valid'
        ),
        CheckConstraint(
            'max_uses >= 0',
            name='ck_max_uses_valid'
        ),
        CheckConstraint(
            'expires_at > created_at',
            name='ck_token_expiry_valid'
        )
    )

    def is_valid(self) -> bool:
        """Check if refresh token is valid for use."""
        now = datetime.utcnow()
        return (
                not self.revoked and
                self.expires_at > now and
                (self.max_uses == 0 or self.use_count < self.max_uses)
        )

    def increment_usage(self) -> None:
        """Record token usage."""
        self.use_count += 1
        self.last_used_at = datetime.utcnow()