# backend/db/models/staging/insight_output_model.py
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Column, String, JSON, DateTime, Integer, Float, ForeignKey, Enum, Boolean, Index
from sqlalchemy.orm import relationship
from .base_staging_model import BaseStagedOutput
from core.messaging.event_types import ComponentType


class StagedInsightOutput(BaseStagedOutput):
    """Insight insight specific output model"""
    __tablename__ = 'staged_insight_outputs'

    base_id = Column(UUID(as_uuid=True), ForeignKey('staged_outputs.id'), primary_key=True)
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

    # Unique source_id for insights
    insight_source_id = Column(  # Changed back to insight_source_id
        UUID(as_uuid=True),
        ForeignKey('data_sources.id'),
        nullable=True,
        name='insight_source_id'  # Explicit column name
    )

    source = relationship(
        "DataSource",
        back_populates="insight_outputs",
        foreign_keys=[insight_source_id]  # Use the unique column name
    )

    __mapper_args__ = {
        "polymorphic_identity": ComponentType.INSIGHT_MANAGER,
        "inherit_condition": base_id == BaseStagedOutput.id
    }

    # Add table arguments for index and constraints
    __table_args__ = (
        Index('ix_staged_insight_outputs_source', 'insight_source_id'),
        {'extend_existing': True}
    )