from sqlalchemy import (
    Column, String, DateTime, Enum, ForeignKey, Text, 
    Integer, Boolean, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel

class Report(BaseModel):
    __tablename__ = 'reports'

    title = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(100))
    status = Column(
        Enum('draft', 'generating', 'completed', 'failed', name='report_status'),
        default='draft'
    )
    format = Column(String(50))
    config = Column(JSONB)
    parameters = Column(JSONB)
    report_meta = Column(JSONB)
    data_sources = Column(JSONB)
    filters = Column(JSONB)
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    template_id = Column(UUID(as_uuid=True), ForeignKey('report_templates.id'))
    
    sections = relationship('ReportSection', back_populates='report', cascade='all, delete-orphan')
    schedule = relationship('ReportSchedule', back_populates='report', uselist=False, cascade='all, delete-orphan')
    executions = relationship('ReportExecution', back_populates='report', cascade='all, delete-orphan')

    __table_args__ = (
        Index('ix_reports_owner_status', 'owner_id', 'status'),
        {'extend_existing': True}
    )

class ReportTemplate(BaseModel):
    __tablename__ = 'report_templates'

    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(100))
    content = Column(JSONB)
    parameters = Column(JSONB)
    template_meta = Column(JSONB)
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    category = Column(String(100))
    thumbnail_url = Column(String(255))

    reports = relationship('Report', backref='template')

class ReportSection(BaseModel):
    __tablename__ = 'report_sections'

    report_id = Column(UUID(as_uuid=True), ForeignKey('reports.id', ondelete='CASCADE'))
    name = Column(String(255))
    type = Column(String(100))
    content = Column(JSONB)
    section_order = Column(Integer)
    config = Column(JSONB)
    visualization_config = Column(JSONB)
    data_source = Column(JSONB)
    filters = Column(JSONB)
    
    report = relationship('Report', back_populates='sections')

    __table_args__ = (
        CheckConstraint('section_order >= 0', name='ck_section_order_positive'),
        Index('ix_report_sections_order', 'report_id', 'section_order'),
        {'extend_existing': True}
    )

class ReportSchedule(BaseModel):
    __tablename__ = 'report_schedules'

    report_id = Column(UUID(as_uuid=True), ForeignKey('reports.id', ondelete='CASCADE'))
    frequency = Column(String(50))
    cron_expression = Column(String(100))
    timezone = Column(String(50))
    is_active = Column(Boolean, default=True)
    next_run = Column(DateTime)
    last_run = Column(DateTime)
    parameters = Column(JSONB)
    notification_config = Column(JSONB)
    
    report = relationship('Report', back_populates='schedule')

class ReportExecution(BaseModel):
    __tablename__ = 'report_executions'

    report_id = Column(UUID(as_uuid=True), ForeignKey('reports.id', ondelete='CASCADE'))
    status = Column(Enum('running', 'completed', 'failed', name='execution_status'))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    parameters = Column(JSONB)
    output_url = Column(String(255))
    error = Column(Text)
    execution_meta = Column(JSONB)
    duration = Column(Integer)  # seconds
    size = Column(Integer)  # bytes
    
    report = relationship('Report', back_populates='executions')

    __table_args__ = (
        CheckConstraint('duration >= 0', name='ck_execution_duration_positive'),
        CheckConstraint('size >= 0', name='ck_execution_size_positive'),
        Index('ix_report_executions_status', 'status'),
        {'extend_existing': True}
    )