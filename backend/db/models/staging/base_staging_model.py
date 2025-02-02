from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Column, JSON, DateTime, Integer, Float, ForeignKey, Enum, Boolean, String
from sqlalchemy.orm import relationship
from datetime import datetime

from ..base import Base
from core.messaging.event_types import ComponentType, ReportSectionType, ProcessingStatus


class BaseStagedOutput(Base):
    """Base model for all staged outputs"""
    __tablename__ = 'staged_outputs'

    # Change id to UUID
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Change pipeline_id to UUID
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id'))

    # Source_id field
    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'), nullable=True)

    # Source relationship
    source = relationship("DataSource", foreign_keys=[source_id])

    # Rest of the model remains the same
    component_type = Column(Enum(ComponentType))
    output_type = Column(Enum(ReportSectionType))
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    storage_path = Column(String)
    data_size = Column(Integer, default=0)
    base_stage_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_temporary = Column(Boolean, default=True)

    metrics = Column(JSON, default={})
    processing_history = relationship("StagingProcessingHistory", back_populates="staged_output")

    __mapper_args__ = {
        "polymorphic_identity": "base",
        "polymorphic_on": component_type
    }