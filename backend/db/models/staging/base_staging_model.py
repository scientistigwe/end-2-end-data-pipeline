# backend/db/models/staging/base_staging_model.py

from sqlalchemy import Column, String, JSON, DateTime, Integer, Float, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..base import Base
from core.messaging.event_types import ComponentType, ReportSectionType, ProcessingStatus


class BaseStagedOutput(Base):
    """Base model for all staged outputs"""
    __tablename__ = 'staged_outputs'

    id = Column(String, primary_key=True)
    pipeline_id = Column(String, ForeignKey('pipelines.id'))
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

    # Relationships
    pipeline = relationship("Pipeline", back_populates="staged_outputs")
    metrics = Column(JSON, default={})
    processing_history = relationship("StagingProcessingHistory", back_populates="staged_output")










