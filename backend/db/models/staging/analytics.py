from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Float, Text,
    Integer, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseStagedOutput, ComponentType


class StagedAnalyticsOutput(BaseStagedOutput):
    """Model for managing analytics processing outputs."""
    __tablename__ = 'staged_analytics_outputs'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
    )

    # Model configuration
    model_type = Column(String(100), nullable=False)
    training_duration = Column(Float)
    iteration_count = Column(Integer)

    # Model metrics and results
    performance_metrics = Column(JSONB)
    feature_importance = Column(JSONB)
    model_parameters = Column(JSONB)
    predictions = Column(JSONB)
    evaluation_results = Column(JSONB)
    model_artifacts = Column(JSONB)

    # Data insights
    data_distribution = Column(JSONB)
    outliers = Column(JSONB)
    correlation_matrix = Column(JSONB)

    # Performance indicators
    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)

    # Source relationship
    analytics_source = relationship(
        "DataSource",
        back_populates="analytics_outputs",
        foreign_keys=[BaseStagedOutput.base_source_id]
    )

    __mapper_args__ = {
        "polymorphic_identity": ComponentType.ANALYTICS,
        "inherit_condition": base_id == BaseStagedOutput.id
    }

    __table_args__ = (
        Index('ix_analytics_outputs_model_type', 'model_type'),
        CheckConstraint(
            'training_duration >= 0 OR training_duration IS NULL',
            name='ck_training_duration_valid'
        ),
        CheckConstraint(
            'iteration_count >= 0 OR iteration_count IS NULL',
            name='ck_iteration_count_valid'
        ),
        CheckConstraint(
            'accuracy BETWEEN 0 AND 1 OR accuracy IS NULL',
            name='ck_accuracy_range'
        ),
        {'extend_existing': True}
    )


class StagedInsightOutput(BaseStagedOutput):
    """Model for managing business insights and pattern detection."""
    __tablename__ = 'staged_insight_outputs'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
    )

    # Insight metrics
    insight_count = Column(Integer)
    goal_alignment_score = Column(Float)
    business_impact_score = Column(Float)
    confidence_score = Column(Float)

    # Analysis results
    insights = Column(JSONB)
    goals_analysis = Column(JSONB)
    metrics_analysis = Column(JSONB)
    patterns_discovered = Column(JSONB)
    correlations = Column(JSONB)
    recommendations = Column(JSONB)

    # Source relationship
    insight_source = relationship(
        "DataSource",
        back_populates="insight_outputs",
        foreign_keys=[BaseStagedOutput.base_source_id]
    )

    __mapper_args__ = {
        "polymorphic_identity": ComponentType.INSIGHT,
        "inherit_condition": base_id == BaseStagedOutput.id
    }

    __table_args__ = (
        CheckConstraint(
            'insight_count >= 0 OR insight_count IS NULL',
            name='ck_insight_count_valid'
        ),
        CheckConstraint(
            'goal_alignment_score BETWEEN 0 AND 1 OR goal_alignment_score IS NULL',
            name='ck_goal_alignment_range'
        ),
        CheckConstraint(
            'business_impact_score BETWEEN 0 AND 1 OR business_impact_score IS NULL',
            name='ck_impact_score_range'
        ),
        CheckConstraint(
            'confidence_score BETWEEN 0 AND 1 OR confidence_score IS NULL',
            name='ck_confidence_score_range'
        ),
        {'extend_existing': True}
    )


class StagedDecisionOutput(BaseStagedOutput):
    """Model for managing decision-making processes and outcomes."""
    __tablename__ = 'staged_decision_outputs'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
    )

    # Decision configuration
    decision_type = Column(String(100), nullable=False)
    context = Column(JSONB)
    criteria = Column(JSONB)
    constraints = Column(JSONB)
    priority = Column(String(50))
    deadline = Column(DateTime)

    # Decision details
    options = Column(JSONB)
    selected_option = Column(JSONB)
    evaluation_matrix = Column(JSONB)
    impact_analysis = Column(JSONB)
    risk_assessment = Column(JSONB)
    confidence_score = Column(Float)

    # Decision metadata
    decision_maker = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    stakeholders = Column(JSONB)
    approval_status = Column(String(50))
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    approved_at = Column(DateTime)
    implementation_plan = Column(JSONB)

    # Source relationship
    decision_source = relationship(
        "DataSource",
        back_populates="decision_outputs",
        foreign_keys=[BaseStagedOutput.base_source_id]
    )

    __mapper_args__ = {
        "polymorphic_identity": ComponentType.DECISION,
        "inherit_condition": base_id == BaseStagedOutput.id
    }

    __table_args__ = (
        Index('ix_decision_outputs_type', 'decision_type'),
        Index('ix_decision_outputs_status', 'approval_status'),
        CheckConstraint(
            'confidence_score BETWEEN 0 AND 1 OR confidence_score IS NULL',
            name='ck_decision_confidence_range'
        ),
        CheckConstraint(
            'deadline > created_at OR deadline IS NULL',
            name='ck_decision_deadline_valid'
        ),
        CheckConstraint(
            'approved_at > created_at OR approved_at IS NULL',
            name='ck_approval_time_valid'
        ),
        {'extend_existing': True}
    )