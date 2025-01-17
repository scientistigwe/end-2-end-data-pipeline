# backend/db/models/staging/insight_output_model.py

from sqlalchemy import Column, String, JSON, DateTime, Integer, Float, ForeignKey, Enum, Boolean
from .base_staging_model import BaseStagedOutput


class StagedInsightOutput(BaseStagedOutput):
    """Insight analysis specific output model"""
    __tablename__ = 'staged_insight_outputs'

    id = Column(String, ForeignKey('staged_outputs.id'), primary_key=True)
    insight_count = Column(Integer)
    goal_alignment_score = Column(Float)
    business_impact_score = Column(Float)
    confidence_score = Column(Float)

    # Insight details
    insights = Column(JSON)
    goals_analysis = Column(JSON)
    metrics_analysis = Column(JSON)
    patterns_discovered = Column(JSON)
    correlations = Column(JSON)
    recommendations = Column(JSON)
