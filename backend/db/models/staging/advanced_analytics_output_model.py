# backend/db/models/staging/advanced_analytics_output_model.py
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Column, String, JSON, DateTime, Integer, Float, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from core.messaging.event_types import ComponentType
from .base_staging_model import BaseStagedOutput


class StagedAnalyticsOutput(BaseStagedOutput):
    """Advanced analytics specific output model"""
    __tablename__ = 'staged_analytics_outputs'
    base_id = Column(UUID(as_uuid=True), ForeignKey('staged_outputs.id'), primary_key=True)

    model_type = Column(String)
    training_duration = Column(Float)
    iteration_count = Column(Integer)

    # Model metrics
    performance_metrics = Column(JSON)
    feature_importance = Column(JSON)
    model_parameters = Column(JSON)
    predictions = Column(JSON)
    evaluation_results = Column(JSON)
    model_artifacts = Column(JSON)

    # Add source relationship explicitly
    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'))
    source = relationship(
        "DataSource",
        back_populates="analytics_outputs",
        foreign_keys=[source_id]
    )

    __mapper_args__ = {
        "polymorphic_identity": ComponentType.ANALYTICS_MANAGER,
        "inherit_condition": base_id == BaseStagedOutput.id
    }