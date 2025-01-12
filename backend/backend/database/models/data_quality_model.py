from sqlalchemy import (
    Column,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Float,
    Text,
    Integer,
    Boolean,
    Index,
    CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel


class QualityRun(BaseModel):
    """Model for quality check execution runs."""
    __tablename__ = 'quality_runs'

    # Basic information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    pipeline_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey('datasets.id'))

    # Run configuration
    check_type = Column(
        Enum('profile', 'validation', 'monitoring', 'custom', name='check_type'),
        nullable=False
    )
    configuration = Column(JSONB)  # Check configuration
    rules = Column(JSONB)  # Applied rules
    thresholds = Column(JSONB)  # Quality thresholds

    # Execution tracking
    status = Column(
        Enum('pending', 'running', 'completed', 'failed', name='quality_status'),
        default='pending'
    )
    progress = Column(Float, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    execution_time = Column(Float)  # in seconds

    # Results summary
    total_checks = Column(Integer, default=0)
    passed_checks = Column(Integer, default=0)
    failed_checks = Column(Integer, default=0)
    warning_checks = Column(Integer, default=0)
    quality_score = Column(Float)  # Overall quality score

    # Error handling
    error = Column(Text)
    error_details = Column(JSONB)

    # Relationships
    profiles = relationship(
        'DataProfile',
        back_populates='quality_run',
        cascade='all, delete-orphan'
    )
    validations = relationship(
        'QualityValidation',
        back_populates='quality_run',
        cascade='all, delete-orphan'
    )
    metrics = relationship(
        'QualityMetric',
        back_populates='quality_run',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('ix_quality_runs_type_status', 'check_type', 'status'),
        CheckConstraint('progress >= 0 AND progress <= 100', name='ck_valid_progress'),
        CheckConstraint('quality_score >= 0 AND quality_score <= 100', name='ck_valid_score'),
        {'extend_existing': True}
    )


class DataProfile(BaseModel):
    """Model for storing data profiling results."""
    __tablename__ = 'data_profiles'

    quality_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('quality_runs.id', ondelete='CASCADE'),
        nullable=False
    )

    # Profile information
    profile_type = Column(String(100), nullable=False)  # e.g., 'column', 'table'
    target_name = Column(String(255), nullable=False)  # Column/table name

    # Statistical metrics
    row_count = Column(Integer)
    null_count = Column(Integer)
    unique_count = Column(Integer)
    data_type = Column(String(50))

    # Distribution metrics
    distribution_type = Column(String(100))
    distribution_params = Column(JSONB)
    quantiles = Column(JSONB)
    histogram = Column(JSONB)

    # Type-specific metrics
    numeric_stats = Column(JSONB)  # For numeric columns
    categorical_stats = Column(JSONB)  # For categorical columns
    text_stats = Column(JSONB)  # For text columns
    temporal_stats = Column(JSONB)  # For datetime columns

    # Quality indicators
    quality_issues = Column(JSONB)
    recommendations = Column(JSONB)

    # Relationships
    quality_run = relationship('QualityRun', back_populates='profiles')


class QualityValidation(BaseModel):
    """Model for storing validation check results."""
    __tablename__ = 'quality_validations'

    quality_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('quality_runs.id', ondelete='CASCADE'),
        nullable=False
    )

    # Validation information
    validation_type = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Rule information
    rule_id = Column(UUID(as_uuid=True))
    rule_config = Column(JSONB)
    parameters = Column(JSONB)

    # Results
    status = Column(
        Enum('passed', 'failed', 'warning', 'error', name='validation_status'),
        nullable=False
    )
    result = Column(JSONB)
    failed_rows = Column(Integer, default=0)
    impact_score = Column(Float)

    # Context
    context = Column(JSONB)  # Additional context about the validation
    affected_columns = Column(JSONB)
    suggestions = Column(JSONB)

    # Relationships
    quality_run = relationship('QualityRun', back_populates='validations')


class QualityMetric(BaseModel):
    """Model for storing quality metrics."""
    __tablename__ = 'quality_metrics'

    quality_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('quality_runs.id', ondelete='CASCADE'),
        nullable=False
    )

    # Metric information
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)

    # Context
    dimension = Column(String(100))  # e.g., 'completeness', 'accuracy'
    target = Column(String(255))  # Target entity (column/table)
    threshold = Column(Float)

    # Metadata
    computation_details = Column(JSONB)
    context = Column(JSONB)
    historical_values = Column(JSONB)

    # Relationships
    quality_run = relationship('QualityRun', back_populates='metrics')

    __table_args__ = (
        Index('ix_quality_metrics_category', 'category'),
        CheckConstraint('value >= 0 AND value <= 100', name='ck_valid_metric_value'),
        {'extend_existing': True}
    )