# backend/db/types/insight_model.py

from sqlalchemy import (
    Column, String, DateTime, Enum, ForeignKey, Float, Text, 
    Integer, Boolean, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import TYPE_CHECKING
from .base import BaseModel

if TYPE_CHECKING:
    from .data_source import DataSource
    from .auth import User

class InsightRun(BaseModel):
    """Model for insight generation runs."""
    __tablename__ = 'insight_runs'

    # Basic information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    pipeline_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'))

    # Run configuration
    analysis_type = Column(
        Enum('trend', 'pattern', 'anomaly', 'correlation', 'segment', name='analysis_type'),
        nullable=False
    )
    configuration = Column(JSONB)
    parameters = Column(JSONB)

    # Execution tracking
    status = Column(
        Enum('pending', 'running', 'completed', 'failed', name='insight_status'),
        default='pending'
    )
    progress = Column(Float, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    execution_time = Column(Float)

    # Results summary
    total_insights = Column(Integer, default=0)
    significant_insights = Column(Integer, default=0)
    actionable_insights = Column(Integer, default=0)
    impact_score = Column(Float)

    error = Column(Text)
    error_details = Column(JSONB)

    # Relationships
    source = relationship(
        'DataSource',
        back_populates='insight_runs',
        foreign_keys=[source_id]
    )
    
    insights = relationship(
        'Insight',
        back_populates='insight_run',
        cascade='all, delete-orphan'
    )
    
    patterns = relationship(
        'InsightPattern',
        back_populates='insight_run',
        cascade='all, delete-orphan'
    )
    
    correlations = relationship(
        'InsightCorrelation',
        back_populates='insight_run',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('ix_insight_runs_type_status', 'analysis_type', 'status'),
        CheckConstraint('progress >= 0 AND progress <= 100', name='ck_valid_progress'),
        CheckConstraint('impact_score >= 0 AND impact_score <= 10', name='ck_valid_impact'),
        {'extend_existing': True}
    )


class Insight(BaseModel):
    """Model for storing individual insights."""
    __tablename__ = 'insights'

    insight_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('insight_runs.id', ondelete='CASCADE'),
        nullable=False
    )
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id'),
        nullable=True
    )

    # Insight information
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    insight_type = Column(String(100), nullable=False)
    category = Column(String(100))

    # Business context
    business_impact = Column(Text)
    recommendations = Column(JSONB)
    priority = Column(
        Enum('low', 'medium', 'high', 'critical', name='insight_priority')
    )

    # Statistical relevance
    confidence = Column(Float)
    significance = Column(Float)
    impact_score = Column(Float)

    # Supporting data
    evidence = Column(JSONB)
    visualization = Column(JSONB)
    related_metrics = Column(JSONB)

    # Action tracking
    status = Column(
        Enum('new', 'reviewed', 'actioned', 'archived', name='insight_action_status'),
        default='new'
    )
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    reviewed_at = Column(DateTime)
    action_taken = Column(Text)
    action_result = Column(JSONB)

    # Relationships
    insight_run = relationship('InsightRun', back_populates='insights')
    source = relationship('DataSource', foreign_keys=[source_id])
    
    goal_mappings = relationship(
        'InsightGoalMapping',
        back_populates='insight',
        cascade='all, delete-orphan'
    )
    
    business_goals = relationship(
        'BusinessGoal',
        secondary='insight_goal_mapping',
        back_populates='insights',
        viewonly=True
    )
    
    actions = relationship(
        'InsightAction',
        back_populates='insight',
        cascade='all, delete-orphan'
    )
    
    impacts = relationship(
        'InsightImpact',
        back_populates='insight',
        cascade='all, delete-orphan'
    )
    
    feedback = relationship(
        'InsightFeedback',
        back_populates='insight',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('ix_insights_type_status', 'insight_type', 'status'),
        CheckConstraint(
            'confidence >= 0 AND confidence <= 1',
            name='ck_valid_confidence'
        ),
        {'extend_existing': True}
    )

class BusinessGoal(BaseModel):
    """Model for tracking business goals related to insights."""
    __tablename__ = 'business_goals'

    # Goal information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    target_value = Column(Float)
    current_value = Column(Float)

    # Goal timeframe
    start_date = Column(DateTime)
    target_date = Column(DateTime)
    achieved_date = Column(DateTime)

    # Goal tracking
    status = Column(
        Enum('active', 'achieved', 'missed', 'cancelled', name='goal_status'),
        default='active'
    )
    progress = Column(Float, default=0)
    priority = Column(Enum('low', 'medium', 'high', name='goal_priority'))

    # Metrics and KPIs
    metrics = Column(JSONB)  # Related metrics
    thresholds = Column(JSONB)  # Success thresholds
    dependencies = Column(JSONB)  # Goal dependencies

    # Relationships
    insight_mappings = relationship(
        'InsightGoalMapping',
        back_populates='goal',
        cascade='all, delete-orphan'
    )
    insights = relationship(
        'Insight',
        secondary='insight_goal_mapping',
        back_populates='business_goals',
        viewonly=True
    )

    __table_args__ = (
        Index('ix_business_goals_status', 'status'),
        CheckConstraint('progress >= 0 AND progress <= 100', name='ck_valid_goal_progress'),
        {'extend_existing': True}
    )


class InsightGoalMapping(BaseModel):
    """Model for mapping insights to business goals."""
    __tablename__ = 'insight_goal_mapping'

    # Primary key columns
    insight_id = Column(
        UUID(as_uuid=True),
        ForeignKey('insights.id', ondelete='CASCADE'),
        primary_key=True
    )
    goal_id = Column(
        UUID(as_uuid=True),
        ForeignKey('business_goals.id', ondelete='CASCADE'),
        primary_key=True
    )

    # Relationship metadata
    relevance_score = Column(Float)
    impact_score = Column(Float)
    contribution_type = Column(String(100))
    validated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    validation_notes = Column(Text)
    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    insight = relationship('Insight', back_populates='goal_mappings')
    goal = relationship('BusinessGoal', back_populates='insight_mappings')

    __table_args__ = (
        CheckConstraint(
            'relevance_score >= 0 AND relevance_score <= 1',
            name='ck_valid_relevance'
        ),
        CheckConstraint(
            'impact_score >= 0 AND impact_score <= 1',
            name='ck_valid_impact'
        ),
        {'extend_existing': True}
    )


class InsightPattern(BaseModel):
    """Model for storing identified patterns."""
    __tablename__ = 'insight_patterns'

    insight_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('insight_runs.id', ondelete='CASCADE'),
        nullable=False
    )

    # Pattern information
    name = Column(String(255), nullable=False)
    pattern_type = Column(String(100), nullable=False)
    description = Column(Text)

    # Pattern details
    frequency = Column(Integer)
    duration = Column(Integer)  # Time span in seconds
    seasonality = Column(JSONB)
    trend = Column(JSONB)

    # Statistical measures
    confidence = Column(Float)
    support = Column(Float)
    strength = Column(Float)

    # Context
    conditions = Column(JSONB)
    exceptions = Column(JSONB)
    related_entities = Column(JSONB)

    # Relationships
    insight_run = relationship('InsightRun', back_populates='patterns')


class InsightCorrelation(BaseModel):
    """Model for storing correlations between entities."""
    __tablename__ = 'insight_correlations'

    insight_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('insight_runs.id', ondelete='CASCADE'),
        nullable=False
    )

    # Correlation information
    name = Column(String(255), nullable=False)
    correlation_type = Column(String(100), nullable=False)
    entity_a = Column(String(255), nullable=False)
    entity_b = Column(String(255), nullable=False)

    # Statistical measures
    correlation_coefficient = Column(Float)
    significance = Column(Float)
    confidence_interval = Column(JSONB)

    # Analysis details
    time_window = Column(String(50))
    lag = Column(Integer)
    seasonally_adjusted = Column(Boolean, default=False)

    # Context
    causality_indicators = Column(JSONB)
    external_factors = Column(JSONB)
    limitations = Column(JSONB)

    # Relationships
    insight_run = relationship('InsightRun', back_populates='correlations')


class InsightAction(BaseModel):
    """Model for tracking actions taken on insights."""
    __tablename__ = 'insight_actions'

    insight_id = Column(
        UUID(as_uuid=True),
        ForeignKey('insights.id', ondelete='CASCADE'),
        nullable=False
    )

    # Action information
    action_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(
        Enum('low', 'medium', 'high', 'critical', name='action_priority')
    )

    # Action tracking
    status = Column(
        Enum('pending', 'in_progress', 'completed', 'cancelled', name='action_status'),
        default='pending'
    )
    assigned_to = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    assigned_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Implementation details
    implementation_plan = Column(JSONB)
    resources_required = Column(JSONB)
    dependencies = Column(JSONB)

    # Results tracking
    result = Column(JSONB)
    impact_measured = Column(JSONB)
    success_metrics = Column(JSONB)

    # Relationships
    insight = relationship('Insight', back_populates='actions')

    __table_args__ = (
        Index('ix_insight_actions_status', 'status'),
        CheckConstraint(
            'completed_at IS NULL OR completed_at >= started_at',
            name='ck_valid_completion_time'
        ),
        {'extend_existing': True}
    )


class InsightImpact(BaseModel):
    """Model for tracking the impact of implemented insights."""
    __tablename__ = 'insight_impacts'

    insight_id = Column(
        UUID(as_uuid=True),
        ForeignKey('insights.id', ondelete='CASCADE'),
        nullable=False
    )

    # Impact measurement
    metric_name = Column(String(255), nullable=False)
    baseline_value = Column(Float)
    current_value = Column(Float)
    target_value = Column(Float)

    # Time tracking
    measurement_date = Column(DateTime, nullable=False)
    baseline_date = Column(DateTime)

    # Impact details
    change_percentage = Column(Float)
    absolute_change = Column(Float)
    impact_duration = Column(Integer)  # Duration in days
    confidence_level = Column(Float)

    # Context
    measurement_method = Column(String(100))
    control_variables = Column(JSONB)
    external_factors = Column(JSONB)
    limitations = Column(JSONB)

    # Relationships
    insight = relationship('Insight', back_populates='impacts')

    __table_args__ = (
        Index('ix_insight_impacts_metric', 'metric_name'),
        CheckConstraint(
            'confidence_level >= 0 AND confidence_level <= 1',
            name='ck_valid_confidence'
        ),
        {'extend_existing': True}
    )


class InsightFeedback(BaseModel):
    """Model for tracking user feedback on insights."""
    __tablename__ = 'insight_feedback'

    insight_id = Column(
        UUID(as_uuid=True),
        ForeignKey('insights.id', ondelete='CASCADE'),
        nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Feedback content
    rating = Column(Integer)  # Numerical rating
    feedback_type = Column(String(100))  # Type of feedback
    comment = Column(Text)
    suggestions = Column(Text)

    # Usefulness metrics
    accuracy_rating = Column(Integer)
    actionability_rating = Column(Integer)
    relevance_rating = Column(Integer)

    # Relationships
    insight = relationship('Insight', back_populates='feedback')

    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='ck_valid_rating'),
        CheckConstraint(
            'accuracy_rating >= 1 AND accuracy_rating <= 5',
            name='ck_valid_accuracy_rating'
        ),
        {'extend_existing': True}
    )