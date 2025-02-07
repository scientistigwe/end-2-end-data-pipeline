from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Float, Text,
    Integer, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseStagedOutput, ComponentType


class StagedMonitoringOutput(BaseStagedOutput):
    """Model for system monitoring and performance tracking."""
    __tablename__ = 'staged_monitoring_outputs'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
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
        foreign_keys=[BaseStagedOutput.base_source_id]
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


class StagedQualityOutput(BaseStagedOutput):
    """Model for data quality assessment and validation."""
    __tablename__ = 'staged_quality_outputs'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
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
        foreign_keys=[BaseStagedOutput.base_source_id]
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


class StagedRecommendationOutput(BaseStagedOutput):
    """Model for managing recommendation generation and tracking."""
    __tablename__ = 'staged_recommendation_outputs'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
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
        foreign_keys=[BaseStagedOutput.base_source_id]
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