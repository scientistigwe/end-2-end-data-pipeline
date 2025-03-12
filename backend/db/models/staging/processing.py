from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Float, Text,
    Integer, Index, CheckConstraint, Enum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseStagedOutput, ComponentType, SourceRelationshipMixin

class StagedAnalyticsOutput(BaseStagedOutput, SourceRelationshipMixin):
    """Model for managing analytics processing outputs."""
    __tablename__ = 'staged_analytics_outputs'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
    )
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='SET NULL'),
        nullable=True
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
        foreign_keys=[source_id],
        primaryjoin="DataSource.id == StagedAnalyticsOutput.source_id"
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


class StagedInsightOutput(BaseStagedOutput, SourceRelationshipMixin):
    """Model for managing business insights and pattern detection."""
    __tablename__ = 'staged_insight_outputs'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
    )
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='SET NULL'),
        nullable=True
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
        foreign_keys=[source_id],
        primaryjoin="DataSource.id == StagedInsightOutput.source_id"
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


class StagedQualityOutput(BaseStagedOutput, SourceRelationshipMixin):
    """Model for data quality assessment and validation."""
    __tablename__ = 'staged_quality_outputs'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
    )
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='SET NULL'),
        nullable=True
    )

    # Quality scores
    quality_score = Column(Float)
    completeness_score = Column(Float)
    accuracy_score = Column(Float)
    consistency_score = Column(Float)
    timeliness_score = Column(Float)
    validity_score = Column(Float)

    # Issue tracking
    issues_found = Column(Integer)
    critical_issues_count = Column(Integer)
    warnings_count = Column(Integer)
    resolved_issues_count = Column(Integer)

    # Quality analysis
    validation_results = Column(JSONB)
    data_profile = Column(JSONB)
    pattern_analysis = Column(JSONB)
    anomaly_detection = Column(JSONB)
    correlation_analysis = Column(JSONB)

    # Recommendations
    improvement_suggestions = Column(JSONB)
    action_items = Column(JSONB)
    priority_fixes = Column(JSONB)
    estimated_impact = Column(JSONB)

    # Source relationship
    quality_source = relationship(
        "DataSource",
        back_populates="quality_outputs",
        foreign_keys=[source_id],
        primaryjoin="DataSource.id == StagedQualityOutput.source_id"
    )

    __mapper_args__ = {
        "polymorphic_identity": ComponentType.QUALITY,
        "inherit_condition": base_id == BaseStagedOutput.id
    }

    __table_args__ = (
        CheckConstraint(
            'quality_score BETWEEN 0 AND 1 OR quality_score IS NULL',
            name='ck_quality_score_range'
        ),
        CheckConstraint(
            'completeness_score BETWEEN 0 AND 1 OR completeness_score IS NULL',
            name='ck_completeness_score_range'
        ),
        CheckConstraint(
            'accuracy_score BETWEEN 0 AND 1 OR accuracy_score IS NULL',
            name='ck_accuracy_score_range'
        ),
        CheckConstraint(
            'issues_found >= 0 OR issues_found IS NULL',
            name='ck_issues_found_valid'
        ),
        CheckConstraint(
            'critical_issues_count >= 0 OR critical_issues_count IS NULL',
            name='ck_critical_issues_valid'
        ),
        {'extend_existing': True}
    )


class StagedMonitoringOutput(BaseStagedOutput, SourceRelationshipMixin):
    """Model for system monitoring and performance tracking."""
    __tablename__ = 'staged_monitoring_outputs'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
    )
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='SET NULL'),
        nullable=True
    )
    # Resource metrics
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    disk_usage = Column(Float)
    network_in = Column(Float)
    network_out = Column(Float)

    # System health
    component_status = Column(JSONB)
    health_checks = Column(JSONB)
    alert_threshold_breaches = Column(JSONB)
    service_availability = Column(Float)

    # Performance metrics
    response_time = Column(Float)
    throughput = Column(Float)
    error_rate = Column(Float)
    concurrent_users = Column(Integer)
    active_connections = Column(Integer)

    # Resource utilization
    resource_allocation = Column(JSONB)
    scaling_metrics = Column(JSONB)
    bottleneck_analysis = Column(JSONB)
    optimization_suggestions = Column(JSONB)

    # Source relationship
    monitoring_source = relationship(
        "DataSource",
        back_populates="monitoring_outputs",
        foreign_keys=[source_id],
        primaryjoin="DataSource.id == StagedMonitoringOutput.source_id"
    )
    __mapper_args__ = {
        "polymorphic_identity": ComponentType.MONITORING,
        "inherit_condition": base_id == BaseStagedOutput.id
    }

    __table_args__ = (
        CheckConstraint(
            'cpu_usage BETWEEN 0 AND 100 OR cpu_usage IS NULL',
            name='ck_cpu_usage_range'
        ),
        CheckConstraint(
            'memory_usage BETWEEN 0 AND 100 OR memory_usage IS NULL',
            name='ck_memory_usage_range'
        ),
        CheckConstraint(
            'disk_usage BETWEEN 0 AND 100 OR disk_usage IS NULL',
            name='ck_disk_usage_range'
        ),
        CheckConstraint(
            'service_availability BETWEEN 0 AND 100 OR service_availability IS NULL',
            name='ck_availability_range'
        ),
        CheckConstraint(
            'error_rate BETWEEN 0 AND 1 OR error_rate IS NULL',
            name='ck_error_rate_range'
        ),
        {'extend_existing': True}
    )


class StagedRecommendationOutput(BaseStagedOutput, SourceRelationshipMixin):
    """Model for managing recommendation generation and tracking."""
    __tablename__ = 'staged_recommendation_outputs'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
    )
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='SET NULL'),
        nullable=True
    )

    # Recommendation details
    recommendation_type = Column(String(100), nullable=False)
    context = Column(JSONB)
    target_audience = Column(JSONB)
    priority = Column(String(50))

    # Generated recommendations
    recommendation_candidates = Column(JSONB)
    top_recommendations = Column(JSONB)
    ranking_criteria = Column(JSONB)
    relevance_scores = Column(JSONB)

    # Metrics
    diversity_score = Column(Float)
    personalization_score = Column(Float)
    confidence_score = Column(Float)
    coverage_score = Column(Float)

    # Performance tracking
    acceptance_rate = Column(Float)
    click_through_rate = Column(Float)
    conversion_rate = Column(Float)
    feedback_metrics = Column(JSONB)

    # Source relationship
    recommendation_source = relationship(
        "DataSource",
        back_populates="recommendation_outputs",
        foreign_keys=[source_id],
        primaryjoin="DataSource.id == StagedRecommendationOutput.source_id"
    )


    __mapper_args__ = {
        "polymorphic_identity": ComponentType.RECOMMENDATION,
        "inherit_condition": base_id == BaseStagedOutput.id
    }

    __table_args__ = (
        Index('ix_recommendation_outputs_type', 'recommendation_type'),
        CheckConstraint(
            'diversity_score BETWEEN 0 AND 1 OR diversity_score IS NULL',
            name='ck_diversity_score_range'
        ),
        CheckConstraint(
            'personalization_score BETWEEN 0 AND 1 OR personalization_score IS NULL',
            name='ck_personalization_score_range'
        ),
        CheckConstraint(
            'confidence_score BETWEEN 0 AND 1 OR confidence_score IS NULL',
            name='ck_confidence_score_range'
        ),
        CheckConstraint(
            'acceptance_rate BETWEEN 0 AND 1 OR acceptance_rate IS NULL',
            name='ck_acceptance_rate_range'
        ),
        {'extend_existing': True}
    )


class StagedDecisionOutput(BaseStagedOutput, SourceRelationshipMixin):
    """Model for managing decision-making processes and outcomes."""
    __tablename__ = 'staged_decision_outputs'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
    )
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='SET NULL'),
        nullable=True
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
    decision_maker = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id')
    )
    stakeholders = Column(JSONB)
    approval_status = Column(String(50))
    approved_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id')
    )
    approved_at = Column(DateTime)
    implementation_plan = Column(JSONB)

    # Source relationship
    decision_source = relationship(
        "DataSource",
        back_populates="decision_outputs",
        foreign_keys=[source_id],
        primaryjoin="DataSource.id == StagedDecisionOutput.source_id"
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
        #CheckConstraint(
        #    'deadline > created_at OR deadline IS NULL',
        #    name='ck_decision_deadline_valid'
        #),
        #CheckConstraint(
        #    'approved_at > created_at OR approved_at IS NULL',
        #    name='ck_approval_time_valid'
        #),
        {'extend_existing': True}
    )