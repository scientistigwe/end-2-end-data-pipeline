from sqlalchemy import (
    Column,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    Integer,
    Boolean,
    Index,
    CheckConstraint,
    Float
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel


class ReportRun(BaseModel):
    """Model for report generation runs."""
    __tablename__ = 'report_runs'

    # Basic information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    pipeline_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Report configuration
    report_type = Column(
        Enum(
            'data_quality', 'pipeline_performance', 'insight_summary',
            'recommendation_summary', 'audit', 'executive_summary',
            name='report_type'
        ),
        nullable=False
    )
    template_id = Column(UUID(as_uuid=True), ForeignKey('report_templates.id'))
    format = Column(String(50))  # e.g., 'pdf', 'html', 'excel'
    parameters = Column(JSONB)
    filters = Column(JSONB)
    data_sources = Column(JSONB)

    # Execution tracking
    status = Column(
        Enum('pending', 'running', 'completed', 'failed', name='report_status'),
        default='pending'
    )
    progress = Column(Float, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    execution_time = Column(Float)  # in seconds

    # Output details
    output_url = Column(String(500))
    output_size = Column(Integer)  # in bytes
    output_format = Column(String(50))

    # Error handling
    error = Column(Text)
    error_details = Column(JSONB)

    # Relationships
    sections = relationship(
        'ReportSection',
        back_populates='report_run',
        cascade='all, delete-orphan'
    )
    visualizations = relationship(
        'ReportVisualization',
        back_populates='report_run',
        cascade='all, delete-orphan'
    )
    validations = relationship(
        'ReportValidation',
        back_populates='report_run',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('ix_report_runs_type_status', 'report_type', 'status'),
        CheckConstraint('progress >= 0 AND progress <= 100', name='ck_valid_progress'),
        CheckConstraint('output_size >= 0', name='ck_valid_size'),
        {'extend_existing': True}
    )


class ReportSection(BaseModel):
    """Model for report sections."""
    __tablename__ = 'report_sections'

    report_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('report_runs.id', ondelete='CASCADE'),
        nullable=False
    )

    # Section information
    title = Column(String(255), nullable=False)
    section_type = Column(String(100), nullable=False)
    content = Column(JSONB)
    order = Column(Integer, nullable=False)

    # Configuration
    template_id = Column(UUID(as_uuid=True))
    parameters = Column(JSONB)
    data_source = Column(JSONB)
    filters = Column(JSONB)

    # Metadata
    is_dynamic = Column(Boolean, default=False)
    requires_refresh = Column(Boolean, default=False)
    cache_duration = Column(Integer)  # in seconds

    # Status tracking
    status = Column(
        Enum('pending', 'generating', 'completed', 'failed', name='section_status'),
        default='pending'
    )
    generation_time = Column(Float)  # in seconds

    # Relationships
    report_run = relationship('ReportRun', back_populates='sections')
    visualizations = relationship(
        'ReportVisualization',
        back_populates='section',
        cascade='all, delete-orphan'
    )


class ReportVisualization(BaseModel):
    """Model for report visualizations."""
    __tablename__ = 'report_visualizations'

    report_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('report_runs.id', ondelete='CASCADE'),
        nullable=False
    )
    section_id = Column(
        UUID(as_uuid=True),
        ForeignKey('report_sections.id', ondelete='CASCADE')
    )

    # Visualization information
    title = Column(String(255), nullable=False)
    viz_type = Column(String(100), nullable=False)  # e.g., 'chart', 'table'
    config = Column(JSONB)  # Visualization configuration
    data = Column(JSONB)  # Visualization data

    # Metadata
    description = Column(Text)
    parameters = Column(JSONB)
    source_query = Column(Text)
    refresh_interval = Column(Integer)  # in seconds

    # Status
    status = Column(
        Enum('pending', 'generating', 'completed', 'failed', name='viz_status'),
        default='pending'
    )
    generation_time = Column(Float)  # in seconds
    last_refresh = Column(DateTime)

    # Relationships
    report_run = relationship('ReportRun', back_populates='visualizations')
    section = relationship('ReportSection', back_populates='visualizations')


class ReportValidation(BaseModel):
    """Model for report data validations."""
    __tablename__ = 'report_validations'

    report_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('report_runs.id', ondelete='CASCADE'),
        nullable=False
    )

    # Validation information
    name = Column(String(255), nullable=False)
    validation_type = Column(String(100), nullable=False)
    parameters = Column(JSONB)

    # Results
    status = Column(
        Enum('passed', 'failed', 'warning', name='validation_status'),
        nullable=False
    )
    results = Column(JSONB)
    error_message = Column(Text)

    # Metadata
    execution_time = Column(Float)  # in seconds
    executed_at = Column(DateTime, default=datetime.utcnow)
    severity = Column(Enum('low', 'medium', 'high', name='severity_level'))

    # Relationships
    report_run = relationship('ReportRun', back_populates='validations')


class ReportSchedule(BaseModel):
    """Model for report scheduling."""
    __tablename__ = 'report_schedules'

    # Schedule information
    report_type = Column(String(100), nullable=False)
    frequency = Column(String(50), nullable=False)  # e.g., 'daily', 'weekly'
    cron_expression = Column(String(100))
    timezone = Column(String(50), default='UTC')

    # Configuration
    parameters = Column(JSONB)
    notification_config = Column(JSONB)
    retry_config = Column(JSONB)

    # Status
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    last_status = Column(String(50))

    # Meta
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    modified_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))


class ReportTemplate(BaseModel):
    """Model for report templates."""
    __tablename__ = 'report_templates'

    # Template information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    template_type = Column(String(100), nullable=False)
    content = Column(JSONB)

    # Configuration
    parameters = Column(JSONB)
    default_config = Column(JSONB)
    validation_rules = Column(JSONB)

    # Version control
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))

    # Meta
    category = Column(String(100))
    tags = Column(JSONB)
    usage_count = Column(Integer, default=0)