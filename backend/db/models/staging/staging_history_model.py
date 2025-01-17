# backend/db/models/staging/staging_history_model.py

from sqlalchemy import Column, String, JSON, DateTime, Integer, Float, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from core.messaging.event_types import ProcessingStatus
from ..base import Base


class StagingProcessingHistory(Base):
    """Track processing history for staged outputs"""
    __tablename__ = 'staging_processing_history'

    id = Column(String, primary_key=True)
    staged_output_id = Column(String, ForeignKey('staged_outputs.id'))
    event_type = Column(String)
    status = Column(Enum(ProcessingStatus))
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    staged_output = relationship("BaseStagedOutput", back_populates="processing_history")
