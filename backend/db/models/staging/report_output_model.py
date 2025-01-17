# backend/db/models/staging/report_output_model.py

from sqlalchemy import Column, String, JSON, DateTime, Integer, Float, ForeignKey, Enum, Boolean
from .base_staging_model import BaseStagedOutput


class StagedReportOutput(BaseStagedOutput):
    """Report specific output model"""
    __tablename__ = 'staged_report_outputs'

    id = Column(String, ForeignKey('staged_outputs.id'), primary_key=True)
    report_type = Column(String)
    format = Column(String)
    version = Column(String)

    # Report components
    sections = Column(JSON)
    visualizations = Column(JSON)
    summary = Column(JSON)
    interactivity_config = Column(JSON)
    distribution_info = Column(JSON)
