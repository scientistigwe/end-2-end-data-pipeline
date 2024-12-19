# models/reports.py
from sqlalchemy import Column, String, DateTime, JSON, Enum, ForeignKey, Float, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel

class Report(BaseModel):
    __tablename__ = 'reports'

    title = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(100))
    status = Column(Enum('draft', 'generating', 'completed', 'failed', name='report_status'))
    format = Column(String(50))  # pdf, excel, etc.
    config = Column(JSONB)
    parameters = Column(JSONB)
    metadata = Column(JSONB)
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    template_id = Column(UUID(as_uuid=True), ForeignKey('report_templates.id'))
    
    sections = relationship('ReportSection', back_populates='report')
    schedule = relationship('ReportSchedule', back_populates='report', uselist=False)

class ReportTemplate(BaseModel):
    __tablename__ = 'report_templates'

    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(100))
    content = Column(JSONB)
    parameters = Column(JSONB)
    metadata = Column(JSONB)
    is_active = Column(Boolean, default=True)

class ReportSection(BaseModel):
    __tablename__ = 'report_sections'

    report_id = Column(UUID(as_uuid=True), ForeignKey('reports.id'), nullable=False)
    name = Column(String(255))
    type = Column(String(100))
    content = Column(JSONB)
    order = Column(Integer)
    config = Column(JSONB)
    
    report = relationship('Report', back_populates='sections')

class ReportSchedule(BaseModel):
    __tablename__ = 'report_schedules'

    report_id = Column(UUID(as_uuid=True), ForeignKey('reports.id'), nullable=False)
    frequency = Column(String(50))  # daily, weekly, monthly
    cron_expression = Column(String(100))
    timezone = Column(String(50))
    is_active = Column(Boolean, default=True)
    next_run = Column(DateTime)
    last_run = Column(DateTime)
    parameters = Column(JSONB)
    
    report = relationship('Report', back_populates='schedule')

class ReportExecution(BaseModel):
    __tablename__ = 'report_executions'

    report_id = Column(UUID(as_uuid=True), ForeignKey('reports.id'), nullable=False)
    status = Column(Enum('running', 'completed', 'failed', name='execution_status'))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    parameters = Column(JSONB)
    output_url = Column(String(255))
    error = Column(Text)
    metadata = Column(JSONB)