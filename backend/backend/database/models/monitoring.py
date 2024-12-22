# models/monitoring.py
from sqlalchemy import Column, String, DateTime, JSON, Enum, ForeignKey, Float, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel

class MonitoringMetric(BaseModel):
    __tablename__ = 'monitoring_metrics'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id'), nullable=False)
    name = Column(String(255), nullable=False)
    value = Column(Float)
    timestamp = Column(DateTime, nullable=False)
    labels = Column(JSONB)
    type = Column(String(50))  # gauge, counter, histogram
    unit = Column(String(50))

class ResourceUsage(BaseModel):
    __tablename__ = 'resource_usage'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    disk_usage = Column(Float)
    network_in = Column(Float)
    network_out = Column(Float)
    resource_meta = Column(JSONB)

class Alert(BaseModel):
    __tablename__ = 'alerts'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id'), nullable=False)
    type = Column(String(100))
    severity = Column(Enum('info', 'warning', 'critical', name='alert_severity'))
    status = Column(Enum('active', 'acknowledged', 'resolved', name='alert_status'))
    message = Column(Text)
    alert_meta = Column(JSONB)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    acknowledged_at = Column(DateTime)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    resolved_at = Column(DateTime)
    resolution_comment = Column(Text)

class AlertRule(BaseModel):
    __tablename__ = 'alert_rules'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id'), nullable=False)
    name = Column(String(255))
    metric = Column(String(255))
    condition = Column(String(50))  # above, below, equals
    threshold = Column(Float)
    duration = Column(Integer)  # in seconds
    severity = Column(Enum('info', 'warning', 'critical', name='rule_severity'))
    enabled = Column(Boolean, default=True)
    description = Column(Text)
    notification_channels = Column(JSONB)

class HealthCheck(BaseModel):
    __tablename__ = 'health_checks'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id'), nullable=False)
    component = Column(String(255))
    status = Column(Enum('healthy', 'degraded', 'failing', name='health_status'))
    last_check = Column(DateTime)
    details = Column(JSONB)
    error = Column(Text)