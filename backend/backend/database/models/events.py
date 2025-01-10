from sqlalchemy import (
    Column, 
    String, 
    DateTime, 
    JSON, 
    Enum, 
    ForeignKey, 
    Text,
    Integer,
    Index,
    Boolean
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel

class Event(BaseModel):
    """Model for tracking system events."""
    __tablename__ = 'events'

    type = Column(
        Enum(
            'pipeline_state',
            'data_sync',
            'validation',
            'security',
            'system',
            name='event_type'
        ),
        nullable=False
    )
    severity = Column(
        Enum('info', 'warning', 'error', 'critical', name='event_severity'),
        default='info'
    )
    source = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    message = Column(Text, nullable=False)
    details = Column(JSONB)
    correlation_id = Column(String(100))
    tags = Column(JSONB)

    # Processing info
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime)
    processing_attempts = Column(Integer, default=0)
    error_details = Column(JSONB)
    retry_until = Column(DateTime)

    __table_args__ = (
        Index('ix_events_type_severity', 'type', 'severity'),
        Index('ix_events_entity', 'entity_type', 'entity_id'),
        Index('ix_events_correlation', 'correlation_id'),
        {'extend_existing': True}
    )

class EventSubscription(BaseModel):
    """Model for event subscriptions and notifications."""
    __tablename__ = 'event_subscriptions'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    event_type = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    min_severity = Column(
        Enum('info', 'warning', 'error', 'critical', name='subscription_severity'),
        default='info'
    )
    notification_method = Column(
        Enum('email', 'slack', 'webhook', name='notification_method'),
        nullable=False
    )
    config = Column(JSONB)
    is_active = Column(Boolean, default=True)

    user = relationship(
        'User',
        foreign_keys=[user_id],  # Explicitly specify foreign keys
        back_populates='event_subscriptions'  # Add back_populates to complete the relationship
    )


class EventProcessor(BaseModel):
    """Model for event processing configurations."""
    __tablename__ = 'event_processors'

    name = Column(String(255), nullable=False)
    event_type = Column(String(100), nullable=False)
    handler_class = Column(String(255), nullable=False)
    config = Column(JSONB)
    is_active = Column(Boolean, default=True)
    event_processor_order = Column(Integer, default=0)
    timeout = Column(Integer)  # seconds
    retry_config = Column(JSONB)

    __table_args__ = (
        Index('ix_event_processors_type', 'event_type'),
        {'extend_existing': True}
    )