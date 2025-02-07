from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, DateTime, JSON, Enum, ForeignKey, Text,
    Integer, Index, Boolean, CheckConstraint, Float
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from .base import BaseModel


class Event(BaseModel):
    """Model for tracking system events and notifications."""
    __tablename__ = 'events'

    # Event Classification
    type = Column(
        Enum(
            'pipeline_state',
            'data_sync',
            'validation',
            'security',
            'system',
            'user_action',
            'resource_change',
            name='event_type'
        ),
        nullable=False
    )
    severity = Column(
        Enum('info', 'warning', 'error', 'critical', name='event_severity'),
        default='info'
    )
    category = Column(String(100))
    subcategory = Column(String(100))

    # Event Context
    source = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    message = Column(Text, nullable=False)
    details = Column(JSONB)
    correlation_id = Column(String(100))
    parent_event_id = Column(UUID(as_uuid=True), ForeignKey('events.id'))

    # Event Metadata
    tags = Column(JSONB)
    environment = Column(String(50))
    component = Column(String(100))
    version = Column(String(50))

    # Processing State
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime)
    processing_attempts = Column(Integer, default=0)
    error_details = Column(JSONB)
    retry_until = Column(DateTime)
    next_retry_at = Column(DateTime)

    # Related Events
    related_events = relationship(
        "Event",
        backref="parent_event",
        remote_side=[id]
    )

    # Subscriptions that match this event
    matching_subscriptions = relationship(
        "EventSubscription",
        secondary="event_subscription_matches",
        back_populates="matched_events"
    )

    __table_args__ = (
        Index('ix_events_type_severity', 'type', 'severity'),
        Index('ix_events_entity', 'entity_type', 'entity_id'),
        Index('ix_events_correlation', 'correlation_id'),
        Index('ix_events_processing', 'processed', 'next_retry_at'),
        CheckConstraint(
            'processing_attempts >= 0',
            name='ck_processing_attempts_valid'
        ),
        CheckConstraint(
            'retry_until IS NULL OR retry_until > created_at',
            name='ck_retry_until_valid'
        )
    )

    @validates('processing_attempts')
    def validate_attempts(self, key: str, value: int) -> int:
        """Validate processing attempts count."""
        if value < 0:
            raise ValueError("Processing attempts cannot be negative")
        return value

    def can_retry(self) -> bool:
        """Check if event can be retried."""
        if not self.retry_until:
            return False
        return (
                not self.processed and
                datetime.utcnow() < self.retry_until and
                self.processing_attempts < 5
        )


class EventSubscription(BaseModel):
    """Model for managing event subscriptions and notifications."""
    __tablename__ = 'event_subscriptions'

    # Subscriber Information
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Subscription Criteria
    event_type = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    min_severity = Column(
        Enum('info', 'warning', 'error', 'critical', name='subscription_severity'),
        default='info'
    )
    filter_conditions = Column(JSONB)

    # Notification Configuration
    notification_method = Column(
        Enum('email', 'slack', 'webhook', name='notification_method'),
        nullable=False
    )
    config = Column(JSONB)
    is_active = Column(Boolean, default=True)

    # Rate Limiting
    cooldown_period = Column(Integer)  # seconds
    last_notification = Column(DateTime)
    notification_count = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="event_subscriptions")
    matched_events = relationship(
        "Event",
        secondary="event_subscription_matches",
        back_populates="matching_subscriptions"
    )

    __table_args__ = (
        Index('ix_event_subscriptions_user_event', 'user_id', 'event_type'),
        Index('ix_event_subscriptions_active', 'is_active'),
        CheckConstraint(
            'cooldown_period >= 0',
            name='ck_cooldown_period_valid'
        ),
        CheckConstraint(
            'notification_count >= 0',
            name='ck_notification_count_valid'
        )
    )

    def can_notify(self) -> bool:
        """Check if notification can be sent based on cooldown."""
        if not self.cooldown_period or not self.last_notification:
            return True

        cooldown_end = self.last_notification + timedelta(seconds=self.cooldown_period)
        return datetime.utcnow() >= cooldown_end


class EventProcessor(BaseModel):
    """Model for configuring event processing and handling."""
    __tablename__ = 'event_processors'

    name = Column(String(255), nullable=False)
    description = Column(Text)
    event_type = Column(String(100), nullable=False)
    handler_class = Column(String(255), nullable=False)

    # Processing Configuration
    config = Column(JSONB)
    is_active = Column(Boolean, default=True)
    processor_order = Column(Integer, default=0)
    timeout = Column(Integer)  # seconds
    max_retries = Column(Integer, default=3)
    retry_delay = Column(Integer, default=60)  # seconds

    # Processing State
    last_run = Column(DateTime)
    last_error = Column(Text)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)

    # Performance Metrics
    average_processing_time = Column(Float)
    peak_processing_time = Column(Float)
    total_events_processed = Column(Integer, default=0)

    __table_args__ = (
        Index('ix_event_processors_type', 'event_type'),
        Index('ix_event_processors_active', 'is_active'),
        CheckConstraint(
            'processor_order >= 0',
            name='ck_processor_order_valid'
        ),
        CheckConstraint(
            'timeout > 0',
            name='ck_timeout_positive'
        ),
        CheckConstraint(
            'max_retries >= 0',
            name='ck_max_retries_valid'
        ),
        CheckConstraint(
            'retry_delay >= 0',
            name='ck_retry_delay_valid'
        ),
        CheckConstraint(
            'success_count >= 0',
            name='ck_success_count_valid'
        ),
        CheckConstraint(
            'error_count >= 0',
            name='ck_error_count_valid'
        ),
        CheckConstraint(
            'total_events_processed >= 0',
            name='ck_total_events_valid'
        )
    )

    def update_metrics(self, processing_time: float, success: bool) -> None:
        """Update processor metrics after event processing."""
        self.last_run = datetime.utcnow()
        self.total_events_processed += 1

        if success:
            self.success_count += 1
        else:
            self.error_count += 1

        # Update average processing time
        if self.average_processing_time is None:
            self.average_processing_time = processing_time
        else:
            total = self.average_processing_time * (self.total_events_processed - 1)
            self.average_processing_time = (total + processing_time) / self.total_events_processed

        # Update peak processing time
        if self.peak_processing_time is None or processing_time > self.peak_processing_time:
            self.peak_processing_time = processing_time


class EventSubscriptionMatch(BaseModel):
    """Association model for tracking which events match which subscriptions."""
    __tablename__ = 'event_subscription_matches'

    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey('events.id', ondelete='CASCADE'),
        primary_key=True
    )
    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey('event_subscriptions.id', ondelete='CASCADE'),
        primary_key=True
    )

    # Match details
    matched_at = Column(DateTime, default=datetime.utcnow)
    match_criteria = Column(JSONB)

    # Notification tracking
    notification_sent = Column(Boolean, default=False)
    notification_time = Column(DateTime)
    delivery_status = Column(
        Enum('pending', 'sent', 'failed', name='delivery_status'),
        default='pending'
    )
    retry_count = Column(Integer, default=0)
    error_details = Column(JSONB)

    __table_args__ = (
        Index('ix_event_sub_matches_notification', 'notification_sent', 'delivery_status'),
        CheckConstraint(
            'retry_count >= 0',
            name='ck_retry_count_valid'
        )
    )


class EventQueue(BaseModel):
    """Model for managing event processing queue."""
    __tablename__ = 'event_queue'

    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey('events.id', ondelete='CASCADE'),
        nullable=False
    )

    # Queue status
    priority = Column(Integer, default=0)
    status = Column(
        Enum('pending', 'processing', 'completed', 'failed', name='queue_status'),
        default='pending'
    )

    # Processing metadata
    processor_id = Column(
        UUID(as_uuid=True),
        ForeignKey('event_processors.id')
    )
    scheduled_time = Column(DateTime)
    processing_started = Column(DateTime)
    processing_completed = Column(DateTime)
    attempt_count = Column(Integer, default=0)

    # Performance tracking
    execution_time = Column(Float)
    memory_usage = Column(Float)
    error_log = Column(JSONB)

    # Relationships
    event = relationship("Event")
    processor = relationship("EventProcessor")

    __table_args__ = (
        Index('ix_event_queue_status_priority', 'status', 'priority'),
        Index('ix_event_queue_scheduled', 'scheduled_time'),
        CheckConstraint(
            'priority >= 0',
            name='ck_priority_valid'
        ),
        CheckConstraint(
            'attempt_count >= 0',
            name='ck_attempt_count_valid'
        ),
        CheckConstraint(
            'execution_time >= 0 OR execution_time IS NULL',
            name='ck_execution_time_valid'
        ),
        CheckConstraint(
            'memory_usage >= 0 OR memory_usage IS NULL',
            name='ck_memory_usage_valid'
        )
    )

    @validates('priority')
    def validate_priority(self, key: str, value: int) -> int:
        """Validate priority value."""
        if value < 0:
            raise ValueError("Priority cannot be negative")
        return value

    def can_process(self) -> bool:
        """Check if event can be processed."""
        return (
                self.status == 'pending' and
                (not self.scheduled_time or self.scheduled_time <= datetime.utcnow()) and
                self.attempt_count < 5
        )