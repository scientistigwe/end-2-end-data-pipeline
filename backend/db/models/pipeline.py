# backend\backend\db\types\pipeline.py
from sqlalchemy import (
    Column, String, DateTime, Enum, ForeignKey, Float, Text, Table,
    Integer, Boolean, Index, UniqueConstraint, event, DDL, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from .base import BaseModel
from datetime import datetime

# Import all staged output models
from .staging.decision_output_model import StagedDecisionOutput
from .staging.recommendation_output_model import StagedRecommendationOutput
from .staging.monitoring_output_model import StagedMonitoringOutput
from .staging.insight_output_model import StagedInsightOutput
from .staging.quality_output_model import StagedQualityOutput
from .staging.advanced_analytics_output_model import StagedAnalyticsOutput
from .staging.report_output_model import StagedReportOutput
from .staging.staging_control_model import StagingControlPoint

# Add before the Pipeline class definition
pipeline_tags = Table(
    'pipeline_tags',
    BaseModel.metadata,
    Column('pipeline_id', UUID(as_uuid=True), ForeignKey('pipelines.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
    Index('ix_pipeline_tags_pipeline', 'pipeline_id'),
    Index('ix_pipeline_tags_tag', 'tag_id')
)


class Tag(BaseModel):
    """Model for pipeline tags."""
    __tablename__ = 'tags'

    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    color = Column(String(7))  # Hex color code

    # Relationships
    pipelines = relationship(
        'Pipeline',
        secondary=pipeline_tags,
        back_populates='tags'
    )


class Pipeline(BaseModel):
    __tablename__ = 'pipelines'

    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(
        Enum('idle', 'running', 'paused', 'completed', 'failed', 'cancelled', name='pipeline_status'),
        default='idle'
    )
    mode = Column(
        Enum('development', 'staging', 'production', name='pipeline_mode'),
        default='development'
    )
    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'))
    target_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'))
    config = Column(JSONB)
    progress = Column(Float, default=0)
    error = Column(Text)
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    version = Column(Integer, default=1)
    
    # Stats
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    average_duration = Column(Float)
    last_success = Column(DateTime)
    failure_count = Column(Integer, default=0)
    
    # Schedule
    schedule_enabled = Column(Boolean, default=False)
    schedule_cron = Column(String(100))
    schedule_timezone = Column(String(50))
    schedule_start = Column(DateTime)
    schedule_end = Column(DateTime)
    
    # Performance
    timeout = Column(Integer)  # seconds
    retry_limit = Column(Integer, default=3)
    retry_delay = Column(Integer)  # seconds
    priority = Column(Integer, default=0)
    concurrent_runs = Column(Boolean, default=False)
    
    # Foreign Keys
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    # Relationships
    owner = relationship('User', back_populates='pipelines', foreign_keys=[owner_id])
    source = relationship('DataSource', foreign_keys=[source_id], back_populates='pipelines_as_source')
    target = relationship('DataSource', foreign_keys=[target_id], back_populates='pipelines_as_target')
    steps = relationship('PipelineStep', back_populates='pipeline', cascade='all, delete-orphan')
    runs = relationship('PipelineRun', back_populates='pipeline', cascade='all, delete-orphan')
    quality_gates = relationship('QualityGate', back_populates='pipeline', cascade='all, delete-orphan')

    base_outputs = relationship(
        "db.models.staging.base_staging_model.BaseStagedOutput",
        backref="pipeline_ref",
        foreign_keys="[db.models.staging.base_staging_model.BaseStagedOutput.pipeline_id]",
        cascade="all, delete-orphan"
    )
    # Update the base_outputs relationship
    staged_outputs = relationship(
        "BaseStagedOutput",
        backref="pipeline",
        foreign_keys="[BaseStagedOutput.pipeline_id]",
        cascade="all, delete-orphan"
    )

    decisions = relationship(
        "db.models.staging.decision_output_model.StagedDecisionOutput",
        primaryjoin="and_(Pipeline.id==StagedDecisionOutput.pipeline_id, "
                   "StagedDecisionOutput.component_type=='decision')",
        viewonly=True
    )

    recommendations = relationship(
        "db.models.staging.recommendation_output_model.StagedRecommendationOutput",
        primaryjoin="and_(Pipeline.id==StagedRecommendationOutput.pipeline_id, "
                   "StagedRecommendationOutput.component_type=='recommendation')",
        viewonly=True
    )

    monitoring_outputs = relationship(
        "db.models.staging.monitoring_output_model.StagedMonitoringOutput",
        primaryjoin="and_(Pipeline.id==StagedMonitoringOutput.pipeline_id, "
                   "StagedMonitoringOutput.component_type=='monitoring')",
        viewonly=True
    )

    insight_outputs = relationship(
        "db.models.staging.insight_output_model.StagedInsightOutput",
        primaryjoin="and_(Pipeline.id==StagedInsightOutput.pipeline_id, "
                   "StagedInsightOutput.component_type=='insight')",
        viewonly=True
    )

    quality_outputs = relationship(
        "db.models.staging.quality_output_model.StagedQualityOutput",
        primaryjoin="and_(Pipeline.id==StagedQualityOutput.pipeline_id, "
                   "StagedQualityOutput.component_type=='quality')",
        viewonly=True
    )

    analytics_outputs = relationship(
        "db.models.staging.advanced_analytics_output_model.StagedAnalyticsOutput",
        primaryjoin="and_(Pipeline.id==StagedAnalyticsOutput.pipeline_id, "
                   "StagedAnalyticsOutput.component_type=='analytics')",
        viewonly=True
    )

    report_outputs = relationship(
        "db.models.staging.report_output_model.StagedReportOutput",
        primaryjoin="and_(Pipeline.id==StagedReportOutput.pipeline_id, "
                   "StagedReportOutput.component_type=='report')",
        viewonly=True
    )

    control_points = relationship(
        "db.models.staging.staging_control_model.StagingControlPoint",
        primaryjoin="and_(Pipeline.id==StagingControlPoint.pipeline_id, "
                   "StagingControlPoint.component_type=='control')",
        viewonly=True
    )

    tags = relationship(
        'Tag',
        secondary='pipeline_tags',
        back_populates='pipelines'
    )
    __table_args__ = (
        Index('ix_pipelines_status', 'status'),
        Index('ix_pipelines_mode', 'mode'),
        Index('ix_pipelines_owner', 'owner_id'),
        UniqueConstraint('name', 'owner_id', name='uq_pipeline_name_owner'),
        CheckConstraint('progress >= 0 AND progress <= 100', name='ck_progress_range'),
        CheckConstraint('timeout > 0', name='ck_timeout_positive'),
        CheckConstraint('retry_limit >= 0', name='ck_retry_limit_positive'),
        CheckConstraint('retry_delay >= 0', name='ck_retry_delay_positive'),
        {'extend_existing': True}
    )

    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name.strip()) < 3:
            raise ValueError("Pipeline name must be at least 3 characters")
        return name.strip()

    @validates('progress')
    def validate_progress(self, key, value):
        if not 0 <= value <= 100:
            raise ValueError("Progress must be between 0 and 100")
        return value

    @hybrid_property
    def is_active(self):
        return self.status in ('running', 'paused')

    @hybrid_property
    def duration(self):
        if self.last_run and self.next_run:
            return (self.next_run - self.last_run).total_seconds()
        return None

    def can_start(self):
        return self.status in ('idle', 'failed', 'completed')

    def can_stop(self):
        return self.status in ('running', 'paused')

class PipelineStep(BaseModel):
   __tablename__ = 'pipeline_steps'

   pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=False)
   name = Column(String(255), nullable=False)
   type = Column(String(100), nullable=False)
   config = Column(JSONB)
   status = Column(
       Enum('pending', 'running', 'completed', 'failed', name='step_status'),
       default='pending'
   )
   pipeline_step_order = Column(Integer, nullable=False)
   enabled = Column(Boolean, default=True)
   timeout = Column(Integer)  # seconds
   retry_attempts = Column(Integer, default=0)
   max_retries = Column(Integer, default=3)
   dependencies = Column(JSONB)  # Array of step IDs
   artifacts = Column(JSONB)
   environment = Column(JSONB)
   resources = Column(JSONB)
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
   runs = relationship('PipelineStepRun', back_populates='step', cascade='all, delete-orphan')
   __table_args__ = (
       Index('ix_pipeline_steps_pipeline', 'pipeline_id'),
       Index('ix_pipeline_steps_order', 'pipeline_id', 'pipeline_step_order'),
       CheckConstraint('pipeline_step_order >= 0', name='ck_step_order_positive'),
       CheckConstraint('timeout > 0', name='ck_step_timeout_positive'),
       CheckConstraint('retry_attempts >= 0', name='ck_retry_attempts_valid'),
       CheckConstraint('max_retries >= 0', name='ck_max_retries_valid'),
       {'extend_existing': True}
   )

class PipelineRun(BaseModel):
   __tablename__ = 'pipeline_runs'

   pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=False)
   version = Column(Integer, nullable=False)
   status = Column(
       Enum('running', 'completed', 'failed', 'cancelled', name='run_status'),
       default='running'
   )
   start_time = Column(DateTime, nullable=False)
   end_time = Column(DateTime)
   duration = Column(Float)  # seconds
   error = Column(JSONB)  # {message: string, step?: string, details?: any}
   metrics = Column(JSONB)  # Performance metrics
   triggered_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
   trigger_type = Column(String(50))  # manual, scheduled, webhook, etc.
   environment_snapshot = Column(JSONB)
   inputs = Column(JSONB)
   outputs = Column(JSONB)
   logs_url = Column(String(255))
   
   # Relationships
   pipeline = relationship('Pipeline', back_populates='runs')
   step_runs = relationship('PipelineStepRun', back_populates='pipeline_run', cascade='all, delete-orphan')
   quality_checks = relationship('QualityCheck', back_populates='pipeline_run', cascade='all, delete-orphan')

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
   __tablename__ = 'pipeline_step_runs'

   pipeline_run_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False)
   step_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_steps.id', ondelete='CASCADE'), nullable=False)
   status = Column(
       Enum('pending', 'running', 'completed', 'failed', name='step_run_status'),
       default='pending'
   )
   start_time = Column(DateTime, nullable=False)
   end_time = Column(DateTime)
   duration = Column(Float)  # seconds
   error = Column(JSONB)
   output = Column(JSONB)
   metrics = Column(JSONB)
   attempt = Column(Integer, default=1)
   node = Column(String(255))  # Execution node/worker
   resources_used = Column(JSONB)
   
   # Relationships
   pipeline_run = relationship(
       'PipelineRun',
       back_populates='step_runs',
       foreign_keys=[pipeline_run_id]
       )
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
   __tablename__ = 'quality_gates'

   pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=False)
   name = Column(String(255), nullable=False)
   description = Column(Text)
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
   
   # Relationships
   pipeline = relationship('Pipeline', back_populates='quality_gates')

   __table_args__ = (
       Index('ix_quality_gates_pipeline', 'pipeline_id'),
       CheckConstraint('threshold >= 0 AND threshold <= 1', name='ck_threshold_range'),
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

class PipelineLog(BaseModel):
    __tablename__ = 'pipeline_logs'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(String(100), nullable=False)
    message = Column(Text)
    details = Column(JSONB)
    timestamp = Column(DateTime, nullable=False, index=True)

    pipeline = relationship('Pipeline', backref='logs')

    __table_args__ = (
        Index('ix_pipeline_logs_pipeline_timestamp', 'pipeline_id', 'timestamp'),
        {'extend_existing': True}
    )

class PipelineVersion(BaseModel):
    __tablename__ = 'pipeline_versions'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=False)
    version_number = Column(Integer, nullable=False)
    config = Column(JSONB)
    created_at = Column(DateTime, nullable=False)

    pipeline = relationship('Pipeline', backref='versions')

    __table_args__ = (
        UniqueConstraint('pipeline_id', 'version_number', name='uq_pipeline_version'),
        Index('ix_pipeline_versions_pipeline', 'pipeline_id'),
        Index('ix_pipeline_versions_created_at', 'created_at'),
        {'extend_existing': True}
    )


class PipelineTemplate(BaseModel):
    __tablename__ = 'pipeline_templates'

    name = Column(String(255), nullable=False)
    description = Column(Text)
    config = Column(JSONB, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    creator = relationship('User', foreign_keys=[created_by])

    __table_args__ = (
        Index('ix_pipeline_templates_name', 'name'),
        UniqueConstraint('name', name='uq_template_name'),
        {'extend_existing': True}
    )