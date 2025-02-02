# backend/db/models/staging/report_output_model.py
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Column, String, JSON, DateTime, Integer, Float, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from .base_staging_model import BaseStagedOutput
from core.messaging.event_types import ComponentType

class StagedReportOutput(BaseStagedOutput):
    """Report specific output model"""
    __tablename__ = 'staged_report_outputs'

    base_id = Column(UUID(as_uuid=True), ForeignKey('staged_outputs.id'), primary_key=True)
    report_type = Column(String)
    format = Column(String)
    version = Column(String)

    # Report components
    sections = Column(JSON)
    visualizations = Column(JSON)
    summary = Column(JSON)
    interactivity_config = Column(JSON)
    distribution_info = Column(JSON)

    __mapper_args__ = {
        "polymorphic_identity": ComponentType.REPORT_MANAGER,
        "inherit_condition": base_id == BaseStagedOutput.id
    }