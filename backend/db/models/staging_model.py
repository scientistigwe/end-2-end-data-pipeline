# backend\backend\db\types\staging_model.py
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Float,
    Text,
    Integer,
    Boolean,
    Index,
    CheckConstraint,
    ForeignKeyConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel


class StagedResource(BaseModel):
    """Model for resources in staging area."""
    __tablename__ = 'staged_resources'

    # Resource identification
    resource_id = Column(UUID(as_uuid=True), primary_key=True)
    pipeline_id = Column(UUID(as_uuid=True), nullable=False)
    stage_key = Column(String(255), nullable=False)  # Unique key within pipeline

    # Resource metadata
    name = Column(String(255))
    resource_type = Column(
        Enum(
            'data', 'model', 'report', 'config', 'visualization',
            name='resource_type'
        ),
        nullable=False
    )
    format = Column(String(50))  # e.g., 'csv', 'json', 'pickle'

    # Storage information
    storage_location = Column(String(500))  # Path or reference to stored data
    size_bytes = Column(Integer)
    checksum = Column(String(64))  # For data integrity

    # Status tracking
    status = Column(
        Enum(
            'pending', 'awaiting_decision', 'approved', 'rejected',
            'processing', 'error', 'expired',
            name='staging_status'
        ),
        default='pending'
    )
    requires_approval = Column(Boolean, default=True)

    # Temporal tracking
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)
    last_accessed = Column(DateTime)

    # Control and metadata
    control_point_id = Column(UUID(as_uuid=True))  # Link to control point
    owner_id = Column(UUID(as_uuid=True))  # User who created/owns resource
    stage_resource_metadata = Column(JSONB)  # Additional resource metadata
    tags = Column(JSONB)  # Resource tags/labels

    # Relationships
    decisions = relationship(
        'StagingDecision',
        back_populates='resource',
        cascade='all, delete-orphan'
    )
    modifications = relationship(
        'StagingModification',
        back_populates='resource',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('ix_staged_resources_pipeline', 'pipeline_id', 'stage_key'),
        Index('ix_staged_resources_status', 'status'),
        CheckConstraint('size_bytes >= 0', name='ck_valid_size'),
        {'extend_existing': True}
    )


class StagingDecision(BaseModel):
    """Model for decisions made on staged resources."""
    __tablename__ = 'staging_decisions'

    # Decision identification
    decision_id = Column(UUID(as_uuid=True), primary_key=True)
    resource_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_resources.resource_id', ondelete='CASCADE'),
        nullable=False
    )

    # Decision details
    decision_type = Column(
        Enum('approve', 'reject', 'modify', name='decision_type'),
        nullable=False
    )
    decision_maker = Column(UUID(as_uuid=True), nullable=False)  # User who made decision
    decision_time = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Decision context
    reason = Column(Text)
    notes = Column(Text)
    stage_decision_metadata = Column(JSONB)  # Additional decision metadata

    # Control point reference
    control_point_ref = Column(UUID(as_uuid=True))  # Reference to control point

    # Relationships
    resource = relationship('StagedResource', back_populates='decisions')

    __table_args__ = (
        Index('ix_staging_decisions_resource', 'resource_id'),
        {'extend_existing': True}
    )


class StagingModification(BaseModel):
    """Model for tracking modifications to staged resources."""
    __tablename__ = 'staging_modifications'

    # Modification identification
    modification_id = Column(UUID(as_uuid=True), primary_key=True)
    resource_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_resources.resource_id', ondelete='CASCADE'),
        nullable=False
    )

    # Modification details
    modification_type = Column(String(100), nullable=False)
    changes = Column(JSONB, nullable=False)  # Actual changes made
    original_values = Column(JSONB)  # Original values before modification

    # Execution tracking
    status = Column(
        Enum('pending', 'applied', 'failed', name='modification_status'),
        default='pending'
    )
    executed_at = Column(DateTime)
    execution_time = Column(Float)  # in seconds
    error = Column(Text)

    # Metadata
    modified_by = Column(UUID(as_uuid=True))  # User who requested modification
    approved_by = Column(UUID(as_uuid=True))  # User who approved modification
    sage_notification_metadata = Column(JSONB)  # Additional modification metadata

    # Relationships
    resource = relationship('StagedResource', back_populates='modifications')

    __table_args__ = (
        Index('ix_staging_modifications_resource', 'resource_id'),
        CheckConstraint('execution_time >= 0', name='ck_valid_execution_time'),
        {'extend_existing': True}
    )


class StagingEvent(BaseModel):
    """Model for tracking staging-related events."""
    __tablename__ = 'staging_events'

    # Event identification
    event_id = Column(UUID(as_uuid=True), primary_key=True)
    resource_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_resources.resource_id', ondelete='CASCADE'),
        nullable=False
    )

    # Event details
    event_type = Column(String(100), nullable=False)
    event_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    actor_id = Column(UUID(as_uuid=True))  # User or system that triggered event

    # Event data
    details = Column(JSONB)
    stage_event_metadata = Column(JSONB)

    # Context
    pipeline_id = Column(UUID(as_uuid=True))
    stage = Column(String(100))

    __table_args__ = (
        Index('ix_staging_events_resource', 'resource_id'),
        Index('ix_staging_events_pipeline', 'pipeline_id'),
        {'extend_existing': True}
    )