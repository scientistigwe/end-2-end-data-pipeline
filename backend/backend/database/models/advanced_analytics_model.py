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


class AnalyticsRun(BaseModel):
    """Model for advanced analytics processing runs."""
    __tablename__ = 'analytics_runs'

    # Basic information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    analysis_type = Column(
        Enum(
            'descriptive', 'diagnostic', 'predictive', 'prescriptive',
            'time_series', 'cohort', 'ab_testing', 'clustering',
            name='analytics_type'
        ),
        nullable=False
    )
    current_phase = Column(
        Enum(
            'data_preparation', 'statistical_analysis', 'predictive_modeling',
            'feature_engineering', 'model_evaluation', 'visualization',
            name='analytics_phase'
        ),
        nullable=False
    )

    # Processing metadata
    pipeline_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'))
    parameters = Column(JSONB)  # Analysis configuration parameters
    analytics_run_metadata = Column(JSONB)  # Additional metadata

    # Execution tracking
    status = Column(
        Enum('pending', 'running', 'completed', 'failed', name='analytics_status'),
        default='pending'
    )
    progress = Column(Float, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    execution_time = Column(Float)  # in seconds
    memory_usage = Column(Float)  # in MB
    error = Column(Text)

    # Relationships
    models = relationship(
        'AnalyticsModel',
        back_populates='run',
        cascade='all, delete-orphan'
    )
    features = relationship(
        'AnalyticsFeature',
        back_populates='run',
        cascade='all, delete-orphan'
    )
    visualizations = relationship(
        'AnalyticsVisualization',
        back_populates='run',
        cascade='all, delete-orphan'
    )
    results = relationship(
        'AnalyticsResult',
        back_populates='run',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('ix_analytics_runs_type_status', 'analysis_type', 'status'),
        CheckConstraint('progress >= 0 AND progress <= 100', name='ck_valid_progress'),
        CheckConstraint(
            'completed_at IS NULL OR completed_at >= started_at',
            name='ck_valid_completion_time'
        ),
        CheckConstraint('execution_time >= 0', name='ck_valid_execution_time'),
        {'extend_existing': True}
    )


class AnalyticsModel(BaseModel):
    """Model for storing trained models and their metrics."""
    __tablename__ = 'analytics_models'

    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('analytics_runs.id', ondelete='CASCADE'),
        nullable=False
    )
    model_type = Column(String(100), nullable=False)  # e.g., 'regression', 'classification'
    framework = Column(String(100))  # e.g., 'sklearn', 'tensorflow'
    parameters = Column(JSONB)  # Model hyperparameters
    metrics = Column(JSONB)  # Performance metrics
    feature_importance = Column(JSONB)  # Feature importance scores

    # Model metadata
    version = Column(String(50))
    training_time = Column(Float)  # in seconds
    training_data_size = Column(Integer)
    validation_data_size = Column(Integer)

    # Model artifacts
    model_path = Column(String(500))  # Path to saved model
    artifacts_path = Column(String(500))  # Path to related artifacts

    # Relationships
    run = relationship('AnalyticsRun', back_populates='models')

    __table_args__ = (
        CheckConstraint('training_time >= 0', name='ck_valid_training_time'),
        CheckConstraint('training_data_size >= 0', name='ck_valid_training_size'),
        {'extend_existing': True}
    )


class AnalyticsFeature(BaseModel):
    """Model for storing engineered features."""
    __tablename__ = 'analytics_features'

    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('analytics_runs.id', ondelete='CASCADE'),
        nullable=False
    )
    name = Column(String(255), nullable=False)
    description = Column(Text)
    feature_type = Column(String(100), nullable=False)  # e.g., 'numeric', 'categorical'
    source_columns = Column(JSONB)  # Original columns used
    transformation = Column(JSONB)  # Transformation details
    statistics = Column(JSONB)  # Feature statistics

    # Feature metadata
    importance_score = Column(Float)
    correlation_scores = Column(JSONB)
    quality_metrics = Column(JSONB)

    # Relationships
    run = relationship('AnalyticsRun', back_populates='features')

    __table_args__ = (
        Index('ix_analytics_features_type', 'feature_type'),
        CheckConstraint(
            'importance_score >= 0 AND importance_score <= 1',
            name='ck_valid_importance'
        ),
        {'extend_existing': True}
    )


class AnalyticsVisualization(BaseModel):
    """Model for storing analytics visualizations."""
    __tablename__ = 'analytics_visualizations'

    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('analytics_runs.id', ondelete='CASCADE'),
        nullable=False
    )
    viz_type = Column(String(100), nullable=False)  # e.g., 'scatter', 'timeseries'
    title = Column(String(255))
    description = Column(Text)
    config = Column(JSONB)  # Visualization configuration
    data = Column(JSONB)  # Visualization data

    # Metadata
    category = Column(String(100))  # e.g., 'trend', 'distribution'
    parameters = Column(JSONB)  # Additional parameters
    dependencies = Column(JSONB)  # Required data/features

    # Relationships
    run = relationship('AnalyticsRun', back_populates='visualizations')


class AnalyticsResult(BaseModel):
    """Model for storing analytics results."""
    __tablename__ = 'analytics_results'

    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('analytics_runs.id', ondelete='CASCADE'),
        nullable=False
    )
    result_type = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    phase = Column(
        Enum(
            'data_preparation', 'statistical_analysis', 'predictive_modeling',
            'feature_engineering', 'model_evaluation', 'visualization',
            name='result_phase'
        ),
        nullable=False
    )

    # Result data
    metrics = Column(JSONB)
    insights = Column(JSONB)
    predictions = Column(JSONB)
    statistical_tests = Column(JSONB)
    data_snapshot = Column(JSONB)  # Summary of data used

    # Execution metadata
    confidence_level = Column(Float)
    sample_size = Column(Integer)
    processing_time = Column(Float)  # in seconds

    # Relationships
    run = relationship('AnalyticsRun', back_populates='results')

    __table_args__ = (
        Index('ix_analytics_results_type_phase', 'result_type', 'phase'),
        CheckConstraint(
            'confidence_level >= 0 AND confidence_level <= 1',
            name='ck_valid_confidence'
        ),
        CheckConstraint('sample_size >= 0', name='ck_valid_sample_size'),
        {'extend_existing': True}
    )