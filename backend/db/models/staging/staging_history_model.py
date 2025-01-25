# backend/db/models/staging/staging_history_model.py

from sqlalchemy.orm import column_property
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey, Enum
from datetime import datetime
from sqlalchemy.orm import relationship
from core.messaging.event_types import ComponentType, ProcessingStatus
from .base_staging_model import BaseStagedOutput


class StagingProcessingHistory(BaseStagedOutput):
    """Track processing history for staged outputs with explicit configuration"""
    __tablename__ = 'staging_processing_history'

    base_id = Column(UUID(as_uuid=True), ForeignKey('staged_outputs.id'), primary_key=True)

    # Remove redundant staged_output_id
    event_type = Column(String)

    # Use unique status column
    history_status = column_property(Column(Enum(ProcessingStatus)))

    details = Column(JSON)

    # Use unique timestamp column
    history_created_at = column_property(Column(DateTime, default=datetime.utcnow))

    # Relationship with explicit back_populates
    staged_output = relationship(
        "BaseStagedOutput",
        back_populates="processing_history",
        foreign_keys=[base_id]
    )

    __mapper_args__ = {
        "polymorphic_identity": "staging.processing_history",  # Unique string identity
        "inherit_condition": base_id == BaseStagedOutput.id
    }