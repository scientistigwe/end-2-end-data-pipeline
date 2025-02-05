from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Column, JSON, DateTime, Integer, Float, ForeignKey, Enum, Boolean, String, Index
from sqlalchemy.orm import relationship, backref
from datetime import datetime

from ..base import BaseModel  # Changed from Base to BaseModel
from core.messaging.event_types import ComponentType, ReportSectionType, ProcessingStatus


class BaseStagedOutput(BaseModel):  # Changed Base to BaseModel
    """Base model for all staged outputs with properly configured relationships."""
    __tablename__ = 'staged_outputs'

    # Remove duplicate columns that are already in BaseModel (id, created_at, updated_at)
    stage_key = Column(String, nullable=False)

    # Configure pipeline relationship properly
    pipeline_id = Column(
        UUID(as_uuid=True),
        ForeignKey('pipelines.id', ondelete='CASCADE'),
        nullable=False
    )

    # Change the column name for source_id
    base_source_id = Column(
        'source_id',  # This is the actual column name in database
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='SET NULL'),
        nullable=True
    )

    # Update relationship to use the new column name
    source = relationship(
        "DataSource",
        foreign_keys=[base_source_id],
        backref="staged_outputs"
    )

    component_type = Column(Enum(ComponentType))
    output_type = Column(Enum(ReportSectionType))
    status = Column(
        Enum(ProcessingStatus),
        default=ProcessingStatus.PENDING,
        nullable=False
    )
    storage_path = Column(String(255))  # Added length constraint
    data_size = Column(Integer, default=0)
    base_stage_metadata = Column(JSON, default={})

    # Remove duplicate timestamps as they're in BaseModel
    expires_at = Column(DateTime, nullable=True)
    is_temporary = Column(Boolean, default=True, nullable=False)
    metrics = Column(JSON, default={})

    # Relationship with explicit back_populates
    processing_history = relationship(
        "StagingProcessingHistory",
        back_populates="staged_output",
        cascade="all, delete-orphan"
    )
    pipeline = relationship(
        "Pipeline",
        back_populates="staged_outputs",
        foreign_keys=[pipeline_id]
    )

    __mapper_args__ = {
        "polymorphic_identity": "base",
        "polymorphic_on": component_type
    }

    __table_args__ = (
        Index('ix_staged_outputs_pipeline_id', 'pipeline_id'),
        Index('ix_staged_outputs_source_id', 'source_id'),
        Index('ix_staged_outputs_status', 'status'),
        Index('ix_staged_outputs_created_at', 'created_at'),
        {'extend_existing': True}
    )