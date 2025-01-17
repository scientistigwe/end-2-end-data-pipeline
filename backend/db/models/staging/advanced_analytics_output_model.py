# backend/db/models/staging/advanced_analytics_output_model.py

from sqlalchemy import Column, String, JSON, DateTime, Integer, Float, ForeignKey, Enum, Boolean


from .base_staging_model import BaseStagedOutput


class StagedAnalyticsOutput(BaseStagedOutput):
    """Advanced analytics specific output model"""
    __tablename__ = 'staged_analytics_outputs'

    id = Column(String, ForeignKey('staged_outputs.id'), primary_key=True)
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

