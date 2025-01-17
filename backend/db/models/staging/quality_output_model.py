# backend/db/models/staging/quality_output_model.py

from sqlalchemy import Column, String, JSON, DateTime, Integer, Float, ForeignKey, Enum, Boolean
from .base_staging_model import BaseStagedOutput


class StagedQualityOutput(BaseStagedOutput):
    """Quality analysis specific output model"""
    __tablename__ = 'staged_quality_outputs'

    id = Column(String, ForeignKey('staged_outputs.id'), primary_key=True)
    quality_score = Column(Float)
    issues_count = Column(Integer)
    critical_issues_count = Column(Integer)
    warnings_count = Column(Integer)
    resolved_issues_count = Column(Integer)
    recommendations_count = Column(Integer)

    # Detailed quality metrics
    completeness_score = Column(Float)
    consistency_score = Column(Float)
    accuracy_score = Column(Float)
    validation_results = Column(JSON)
    profile_data = Column(JSON)
    issue_summary = Column(JSON)
    recommendations = Column(JSON)

