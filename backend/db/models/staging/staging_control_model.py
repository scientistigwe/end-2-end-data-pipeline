# backend/db/models/staging/staging_control_model.py

from sqlalchemy.orm import column_property
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from .base_staging_model import BaseStagedOutput


class StagingControlPoint(BaseStagedOutput):
    """Control points for staged outputs with explicit column configuration"""
    __tablename__ = 'staging_control_points'

    base_id = Column(UUID(as_uuid=True), ForeignKey('staged_outputs.id'), primary_key=True)

    # Explicitly rename and configure columns to avoid implicit combination
    control_type = Column(String)
    control_status = column_property(Column(String))  # Unique status column
    staging_control_metadata = Column(JSON)
    decision = Column(JSON, nullable=True)

    # Use unique timestamp columns
    control_created_at = column_property(Column(DateTime, default=datetime.now))
    control_updated_at = column_property(Column(DateTime, default=datetime.now, onupdate=datetime.now))

    __mapper_args__ = {
        "polymorphic_identity": "staging.control_point",  # Unique string identity
        "inherit_condition": base_id == BaseStagedOutput.id
    }
