from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, DateTime, Enum, ForeignKey, Float, Text,
    Integer, Boolean, Index, UniqueConstraint, CheckConstraint, Table
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from ..core.base import BaseModel

# Association table for pipeline tags
pipeline_tags = Table(
    'pipeline_tags',
    BaseModel.metadata,
    Column('pipeline_id', UUID(as_uuid=True),
           ForeignKey('pipelines.id', ondelete='CASCADE'),
           primary_key=True),
    Column('tag_id', UUID(as_uuid=True),
           ForeignKey('tags.id', ondelete='CASCADE'),
           primary_key=True),
    Index('ix_pipeline_tags_pipeline', 'pipeline_id'),
    Index('ix_pipeline_tags_tag', 'tag_id')
)


class Pipeline(BaseModel):
    """Model for managing data processing pipelines."""
    __tablename__ = 'pipelines'

    # Basic information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(
        Enum('idle', 'running', 'paused', 'completed', 'failed', 'cancelled',
             name='pipeline_status'),
        default='idle'
    )
    mode = Column(
        Enum('development', 'staging', 'production',
             name='pipeline_mode'),
        default='development'
    )
    versions = relationship(
        'PipelineVersion',
        back_populates='pipeline',
        cascade='all, delete-orphan'
    )
    # Configuration
    config = Column(JSONB)
    version = Column(Integer, default=1)
    progress = Column(Float, default=0)
    error = Column(Text)
    timeout = Column(Integer)  # seconds
    retry_limit = Column(Integer, default=3)
    retry_delay = Column(Integer)  # seconds
    priority = Column(Integer, default=0)
    concurrent_runs = Column(Boolean, default=False)

    # Statistics
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    average_duration = Column(Float)
    last_success = Column(DateTime)
    failure_count = Column(Integer, default=0)

    # Scheduling
    schedule_enabled = Column(Boolean, default=False)
    schedule_cron = Column(String(100))
    schedule_timezone = Column(String(50))
    schedule_start = Column(DateTime)
    schedule_end = Column(DateTime)

    # Foreign Keys
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    pipeline_source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'))
    pipeline_target_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'))

    # Relationships
    owner = relationship('User', back_populates='pipelines', foreign_keys=[owner_id])
    pipeline_source = relationship(
        'DataSource',
        foreign_keys=[pipeline_source_id],
        back_populates='pipelines_as_source'
    )
    pipeline_target = relationship(
        'DataSource',
        foreign_keys=[pipeline_target_id],
        back_populates='pipelines_as_target'
    )
    steps = relationship('PipelineStep', back_populates='pipeline',
                        cascade='all, delete-orphan')
    runs = relationship('PipelineRun', back_populates='pipeline',
                       cascade='all, delete-orphan')
    quality_gates = relationship('QualityGate', back_populates='pipeline',
                               cascade='all, delete-orphan')
    tags = relationship('Tag', secondary='pipeline_tags', back_populates='pipelines')
    staged_outputs = relationship(
        "BaseStagedOutput",
        back_populates="pipeline",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_pipelines_status', 'status'),
        Index('ix_pipelines_mode', 'mode'),
        Index('ix_pipelines_owner', 'owner_id'),
        UniqueConstraint('name', 'owner_id', name='uq_pipeline_name_owner'),
        CheckConstraint('progress >= 0 AND progress <= 100',
                       name='ck_progress_range'),
        CheckConstraint('timeout > 0', name='ck_timeout_positive'),
        CheckConstraint('retry_limit >= 0', name='ck_retry_limit_positive'),
        CheckConstraint('retry_delay >= 0', name='ck_retry_delay_positive'),
        {'extend_existing': True}
    )

    @validates('name')
    def validate_name(self, key: str, name: str) -> str:
        """Validate pipeline name."""
        if not name or len(name.strip()) < 3:
            raise ValueError("Pipeline name must be at least 3 characters")
        return name.strip()

    def can_start(self) -> bool:
        """Check if pipeline can be started."""
        return self.status in ('idle', 'failed', 'completed')

    def can_stop(self) -> bool:
        """Check if pipeline can be stopped."""
        return self.status in ('running', 'paused')

    def update_stats(self, duration: float, success: bool) -> None:
        """Update pipeline execution statistics."""
        self.total_runs += 1
        if success:
            self.successful_runs += 1
            self.last_success = datetime.utcnow()
        else:
            self.failure_count += 1

        # Update average duration
        if self.average_duration is None:
            self.average_duration = duration
        else:
            self.average_duration = (
                (self.average_duration * (self.total_runs - 1) + duration)
                / self.total_runs
            )


class Tag(BaseModel):
    """Model for pipeline categorization and organization."""
    __tablename__ = 'tags'

    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    color = Column(String(7))  # Hex color code
    category = Column(String(50))
    meta_data = Column(JSONB)

    # Relationships
    pipelines = relationship(
        'Pipeline',
        secondary=pipeline_tags,
        back_populates='tags'
    )

    __table_args__ = (
        Index('ix_tags_name', 'name'),
        Index('ix_tags_category', 'category'),
        {'extend_existing': True}
    )


class PipelineStep(BaseModel):
    """Model for managing individual pipeline steps."""
    __tablename__ = 'pipeline_steps'

    pipeline_id = Column(UUID(as_uuid=True),
                         ForeignKey('pipelines.id', ondelete='CASCADE'),
                         nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    config = Column(JSONB)
    pipeline_step_order = Column(Integer, nullable=False)

    # Step configuration
    enabled = Column(Boolean, default=True)
    timeout = Column(Integer)  # seconds
    retry_attempts = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    dependencies = Column(JSONB)  # Array of step IDs
    artifacts = Column(JSONB)
    environment = Column(JSONB)
    resources = Column(JSONB)

    # Error handling
    timeout_policy = Column(
        Enum('fail', 'skip', 'retry', name='timeout_policy'),
        default='fail'
    )
    error_policy = Column(
        Enum('fail', 'skip', 'retry', name='error_policy'),
        default='fail'
    )

    # Relationships
    pipeline = relationship('Pipeline', back_populates='steps')
    runs = relationship('PipelineStepRun', back_populates='step',
                        cascade='all, delete-orphan')

    __table_args__ = (
        Index('ix_pipeline_steps_pipeline', 'pipeline_id'),
        Index('ix_pipeline_steps_order', 'pipeline_id', 'pipeline_step_order'),
        CheckConstraint('pipeline_step_order >= 0',
                        name='ck_step_order_positive'),
        CheckConstraint('timeout > 0', name='ck_step_timeout_positive'),
        CheckConstraint('retry_attempts >= 0', name='ck_retry_attempts_valid'),
        CheckConstraint('max_retries >= 0', name='ck_max_retries_valid'),
        {'extend_existing': True}
    )


class PipelineRun(BaseModel):
    """Model for tracking pipeline execution instances."""
    __tablename__ = 'pipeline_runs'

    pipeline_id = Column(UUID(as_uuid=True),
                         ForeignKey('pipelines.id', ondelete='CASCADE'),
                         nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(
        Enum('running', 'completed', 'failed', 'cancelled', name='run_status'),
        default='running'
    )

    # Execution timing
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration = Column(Float)  # seconds

    # Run details
    error = Column(JSONB)
    metrics = Column(JSONB)
    triggered_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    trigger_type = Column(String(50))
    environment_snapshot = Column(JSONB)
    inputs = Column(JSONB)
    outputs = Column(JSONB)
    logs_url = Column(String(255))

    # Relationships
    pipeline = relationship('Pipeline', back_populates='runs')
    step_runs = relationship('PipelineStepRun', back_populates='pipeline_run',
                             cascade='all, delete-orphan')
    quality_checks = relationship('QualityCheck', back_populates='pipeline_run',
                                  cascade='all, delete-orphan')

    __table_args__ = (
        Index('ix_pipeline_runs_status', 'status'),
        Index('ix_pipeline_runs_pipeline', 'pipeline_id'),
        CheckConstraint('duration >= 0', name='ck_run_duration_positive'),
        CheckConstraint(
            'end_time IS NULL OR end_time >= start_time',
            name='ck_run_time_valid'
        ),
        {'extend_existing': True}
    )


class PipelineStepRun(BaseModel):
    """Model for tracking individual step execution results."""
    __tablename__ = 'pipeline_step_runs'

    pipeline_run_id = Column(UUID(as_uuid=True),
                             ForeignKey('pipeline_runs.id', ondelete='CASCADE'),
                             nullable=False)
    step_id = Column(UUID(as_uuid=True),
                     ForeignKey('pipeline_steps.id', ondelete='CASCADE'),
                     nullable=False)

    # Execution state
    status = Column(
        Enum('pending', 'running', 'completed', 'failed', name='step_run_status'),
        default='pending'
    )
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration = Column(Float)  # seconds

    # Run details
    error = Column(JSONB)
    output = Column(JSONB)
    metrics = Column(JSONB)
    attempt = Column(Integer, default=1)
    node = Column(String(255))
    resources_used = Column(JSONB)

    # Relationships
    pipeline_run = relationship('PipelineRun', back_populates='step_runs')
    step = relationship('PipelineStep', back_populates='runs')

    __table_args__ = (
        Index('ix_pipeline_step_runs_status', 'status'),
        CheckConstraint('duration >= 0', name='ck_step_run_duration_positive'),
        CheckConstraint('attempt > 0', name='ck_attempt_positive'),
        CheckConstraint(
            'end_time IS NULL OR end_time >= start_time',
            name='ck_step_run_time_valid'
        ),
        {'extend_existing': True}
    )


class QualityGate(BaseModel):
    """Model for managing pipeline quality gates and criteria."""
    __tablename__ = 'quality_gates'

    pipeline_id = Column(UUID(as_uuid=True),
                         ForeignKey('pipelines.id', ondelete='CASCADE'),
                         nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Gate configuration
    rules = Column(JSONB)
    threshold = Column(Float)
    is_active = Column(Boolean, default=True)
    severity = Column(
        Enum('low', 'medium', 'high', 'critical', name='gate_severity'),
        default='medium'
    )
    action = Column(
        Enum('warn', 'block', 'notify', name='gate_action'),
        default='warn'
    )
    notification_config = Column(JSONB)

    # Relationship
    pipeline = relationship('Pipeline', back_populates='quality_gates')

    __table_args__ = (
        Index('ix_quality_gates_pipeline', 'pipeline_id'),
        CheckConstraint(
            'threshold >= 0 AND threshold <= 1',
            name='ck_threshold_range'
        ),
        {'extend_existing': True}
    )


class QualityCheck(BaseModel):
    """Model for tracking quality check results for pipeline runs."""
    __tablename__ = 'quality_checks'

    pipeline_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('pipeline_runs.id', ondelete='CASCADE'),
        nullable=False
    )
    gate_id = Column(
        UUID(as_uuid=True),
        ForeignKey('quality_gates.id', ondelete='CASCADE'),
        nullable=False
    )

    # Check results
    status = Column(
        Enum('passed', 'failed', 'warning', name='check_status'),
        nullable=False
    )
    check_time = Column(DateTime, nullable=False)
    metrics = Column(JSONB)
    threshold_value = Column(Float)
    actual_value = Column(Float)
    details = Column(JSONB)

    # Relationships
    pipeline_run = relationship('PipelineRun', back_populates='quality_checks')
    quality_gate = relationship('QualityGate')

    __table_args__ = (
        Index('ix_quality_checks_run', 'pipeline_run_id'),
        Index('ix_quality_checks_gate', 'gate_id'),
        Index('ix_quality_checks_status', 'status'),
        {'extend_existing': True}
    )


class PipelineTemplate(BaseModel):
    """Model for managing reusable pipeline templates."""
    __tablename__ = 'pipeline_templates'

    name = Column(String(255), nullable=False)
    description = Column(Text)
    config = Column(JSONB, nullable=False)
    version = Column(Integer, default=1)

    # Template metadata
    category = Column(String(100))
    complexity_level = Column(
        Enum('basic', 'intermediate', 'advanced', name='template_complexity'),
        default='basic'
    )
    estimated_duration = Column(Integer)  # minutes
    required_resources = Column(JSONB)

    # Template permissions
    public = Column(Boolean, default=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey('teams.id'))

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime)
    average_success_rate = Column(Float)

    # Relationships
    creator = relationship('User', foreign_keys=[created_by])
    team = relationship('Team')

    __table_args__ = (
        Index('ix_pipeline_templates_name', 'name'),
        UniqueConstraint('name', name='uq_template_name'),
        CheckConstraint(
            'estimated_duration > 0',
            name='ck_duration_positive'
        ),
        CheckConstraint(
            'usage_count >= 0',
            name='ck_usage_count_non_negative'
        ),
        CheckConstraint(
            'average_success_rate >= 0 AND average_success_rate <= 100',
            name='ck_success_rate_range'
        ),
        {'extend_existing': True}
    )


class PipelineSchedule(BaseModel):
    """Model for managing pipeline execution schedules."""
    __tablename__ = 'pipeline_schedules'

    pipeline_id = Column(UUID(as_uuid=True),
                         ForeignKey('pipelines.id', ondelete='CASCADE'),
                         nullable=False)

    # Schedule configuration
    name = Column(String(255), nullable=False)
    cron_expression = Column(String(100), nullable=False)
    timezone = Column(String(50), nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # Schedule state
    enabled = Column(Boolean, default=True)
    last_execution = Column(DateTime)
    next_execution = Column(DateTime)
    execution_count = Column(Integer, default=0)

    # Execution parameters
    parameters = Column(JSONB)
    timeout = Column(Integer)  # seconds
    max_concurrent = Column(Integer, default=1)

    # Error handling
    retry_on_failure = Column(Boolean, default=False)
    max_retries = Column(Integer, default=0)
    retry_delay = Column(Integer)  # seconds

    # Notifications
    notification_config = Column(JSONB)

    # Relationships
    pipeline = relationship('Pipeline')

    __table_args__ = (
        Index('ix_pipeline_schedules_pipeline', 'pipeline_id'),
        Index('ix_pipeline_schedules_next_execution', 'next_execution'),
        CheckConstraint(
            'end_date IS NULL OR end_date > start_date',
            name='ck_schedule_dates_valid'
        ),
        CheckConstraint(
            'execution_count >= 0',
            name='ck_execution_count_non_negative'
        ),
        CheckConstraint(
            'timeout > 0',
            name='ck_schedule_timeout_positive'
        ),
        CheckConstraint(
            'max_concurrent > 0',
            name='ck_max_concurrent_positive'
        ),
        {'extend_existing': True}
    )

    def is_active(self) -> bool:
        """Check if schedule is currently active."""
        now = datetime.utcnow()
        return (
                self.enabled and
                (not self.start_date or self.start_date <= now) and
                (not self.end_date or self.end_date > now)
        )

    def update_execution_stats(self) -> None:
        """Update schedule execution statistics."""
        self.execution_count += 1
        self.last_execution = datetime.utcnow()


class PipelineLog(BaseModel):
    """Model for comprehensive pipeline logging."""
    __tablename__ = 'pipeline_logs'

    pipeline_id = Column(UUID(as_uuid=True),
                         ForeignKey('pipelines.id', ondelete='CASCADE'),
                         nullable=False)

    # Log details
    level = Column(
        Enum('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', name='log_level'),
        nullable=False
    )
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)

    # Context information
    component = Column(String(100))
    step_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_steps.id'))
    run_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_runs.id'))

    # Additional context
    context = Column(JSONB)
    trace_id = Column(String(100))
    span_id = Column(String(100))

    # Relationships
    pipeline = relationship('Pipeline')
    step = relationship('PipelineStep')
    run = relationship('PipelineRun')

    __table_args__ = (
        Index('ix_pipeline_logs_pipeline_timestamp', 'pipeline_id', 'timestamp'),
        Index('ix_pipeline_logs_level', 'level'),
        Index('ix_pipeline_logs_trace', 'trace_id'),
        {'extend_existing': True}
    )


class PipelineVersion(BaseModel):
    """Model for tracking pipeline versions and changes."""
    __tablename__ = 'pipeline_versions'

    # Foreign key to the main pipeline
    pipeline_id = Column(
        UUID(as_uuid=True),
        ForeignKey('pipelines.id', ondelete='CASCADE'),
        nullable=False
    )

    # Version information
    version_number = Column(Integer, nullable=False)
    version_hash = Column(String(64))  # Git-style hash for version tracking
    snapshot = Column(JSONB, nullable=False)  # Complete pipeline configuration
    change_summary = Column(Text)
    changelog = Column(JSONB)  # Detailed list of changes

    # Version metadata
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=False
    )
    is_active = Column(Boolean, default=False)
    is_deployable = Column(Boolean, default=True)
    deployment_requirements = Column(JSONB)

    # Performance metrics
    performance_metrics = Column(JSONB)
    average_runtime = Column(Float)
    success_rate = Column(Float)

    # Relationships
    pipeline = relationship('Pipeline', back_populates='versions')
    creator = relationship('User', foreign_keys=[created_by])
    dependencies = relationship(
        'PipelineDependency',
        back_populates='dependent_version',
        foreign_keys='[PipelineDependency.dependent_version_id]'
    )

    __table_args__ = (
        Index('ix_pipeline_versions_pipeline', 'pipeline_id'),
        UniqueConstraint(
            'pipeline_id',
            'version_number',
            name='uq_pipeline_version_number'
        ),
        CheckConstraint(
            'version_number > 0',
            name='ck_version_number_positive'
        ),
        CheckConstraint(
            'average_runtime >= 0',
            name='ck_avg_runtime_non_negative'
        ),
        CheckConstraint(
            'success_rate >= 0 AND success_rate <= 100',
            name='ck_success_rate_range'
        ),
        {'extend_existing': True}
    )

    def promote_to_active(self) -> None:
        """Promote this version to active status."""
        # First, deactivate current active version
        PipelineVersion.query.filter(
            PipelineVersion.pipeline_id == self.pipeline_id,
            PipelineVersion.is_active == True,
            PipelineVersion.id != self.id
        ).update({'is_active': False})

        # Set this version as active
        self.is_active = True

    def update_metrics(self, runtime: float, success: bool) -> None:
        """Update version performance metrics."""
        metrics = self.performance_metrics or {'total_runs': 0, 'successful_runs': 0}
        metrics['total_runs'] += 1
        if success:
            metrics['successful_runs'] += 1

        # Update average runtime
        if self.average_runtime is None:
            self.average_runtime = runtime
        else:
            total_runs = metrics['total_runs']
            self.average_runtime = (
                    (self.average_runtime * (total_runs - 1) + runtime) / total_runs
            )

        # Update success rate
        self.success_rate = (
                (metrics['successful_runs'] / metrics['total_runs']) * 100
        )
        self.performance_metrics = metrics


class PipelineDependency(BaseModel):
    """Model for managing pipeline version dependencies."""
    __tablename__ = 'pipeline_dependencies'

    # Source version (the one that depends on another)
    dependent_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey('pipeline_versions.id', ondelete='CASCADE'),
        nullable=False
    )

    # Target version (the one being depended upon)
    dependency_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey('pipeline_versions.id', ondelete='CASCADE'),
        nullable=False
    )

    # Dependency configuration
    dependency_type = Column(
        Enum(
            'required',
            'optional',
            'conditional',
            name='dependency_type'
        ),
        default='required'
    )
    conditions = Column(JSONB)  # For conditional dependencies
    config = Column(JSONB)  # Dependency-specific configuration

    # Dependency status
    is_active = Column(Boolean, default=True)
    last_verified = Column(DateTime)
    compatibility_status = Column(
        Enum(
            'compatible',
            'incompatible',
            'unknown',
            name='compatibility_status'
        ),
        default='unknown'
    )

    # Runtime behavior
    wait_for_completion = Column(Boolean, default=True)
    timeout = Column(Integer)  # seconds
    retry_strategy = Column(JSONB)

    # Relationships
    dependent_version = relationship(
        'PipelineVersion',
        foreign_keys=[dependent_version_id],
        back_populates='dependencies'
    )
    dependency_version = relationship(
        'PipelineVersion',
        foreign_keys=[dependency_version_id]
    )

    __table_args__ = (
        Index(
            'ix_pipeline_dependencies_dependent',
            'dependent_version_id'
        ),
        Index(
            'ix_pipeline_dependencies_dependency',
            'dependency_version_id'
        ),
        UniqueConstraint(
            'dependent_version_id',
            'dependency_version_id',
            name='uq_pipeline_dependency'
        ),
        CheckConstraint(
            'dependent_version_id != dependency_version_id',
            name='ck_no_self_dependency'
        ),
        CheckConstraint(
            'timeout > 0',
            name='ck_timeout_positive'
        ),
        {'extend_existing': True}
    )

    def verify_compatibility(self) -> bool:
        """Verify compatibility between dependent and dependency versions."""
        try:
            # Implementation would check version compatibility
            # Update last_verified and compatibility_status
            self.last_verified = datetime.utcnow()
            # For now, just checking if both versions are deployable
            if (self.dependent_version.is_deployable and
                    self.dependency_version.is_deployable):
                self.compatibility_status = 'compatible'
                return True
            self.compatibility_status = 'incompatible'
            return False
        except Exception:
            self.compatibility_status = 'unknown'
            return False