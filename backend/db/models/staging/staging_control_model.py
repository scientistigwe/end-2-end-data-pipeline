# backend/db/models/staging/staging_control_model.py

from sqlalchemy import Column, String, JSON, DateTime, Integer, Float, ForeignKey, Enum, Boolean
from datetime import datetime
from .base_staging_model import BaseStagedOutput
from ..base import Base

class StagingControlPoint(Base):
    """Control points for staged outputs"""
    __tablename__ = 'staging_control_points'

    id = Column(String, primary_key=True)
    staged_output_id = Column(String, ForeignKey('staged_outputs.id'))
    control_type = Column(String)
    status = Column(String)
    staging_control_metadata = Column(JSON)
    decision = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)