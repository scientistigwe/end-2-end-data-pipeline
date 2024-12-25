from sqlalchemy import (
    Column, String, DateTime, Enum, ForeignKey, Float, Text, 
    Integer, Boolean, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel

class MonitoringMetric(BaseModel):
    __tablename__ = 'monitoring_metrics'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id', ondelete='CASCADE'))
    name = Column(String(255), nullable=False)
    value = Column(Float)
    timestamp = Column(DateTime, nullable=False)
    type = Column(Enum('gauge', 'counter', 'histogram', name='metric_type'))
    unit = Column(String(50))
    labels = Column(JSONB)
    aggregation_window = Column(String(50))
    thresholds = Column(JSONB)

    __table_args__ = (
        Index('ix_monitoring_metrics_pipeline_timestamp', 'pipeline_id', 'timestamp'),
        CheckConstraint('value IS NULL OR value >= 0', name='ck_metric_value_positive'),
        {'extend_existing': True}
    )

class ResourceUsage(BaseModel):
    __tablename__ = 'resource_usage'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id', ondelete='CASCADE'))
    timestamp = Column(DateTime, nullable=False)
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    disk_usage = Column(Float)
    network_in = Column(Float)
    network_out = Column(Float)
    resource_meta = Column(JSONB)

    pipeline = relationship('Pipeline', back_populates='resource_usage')

    __table_args__ = (
        CheckConstraint('cpu_usage >= 0 AND cpu_usage <= 100', name='ck_cpu_usage_range'),
        CheckConstraint('memory_usage >= 0', name='ck_memory_usage_positive'),
        CheckConstraint('disk_usage >= 0', name='ck_disk_usage_positive'),
        Index('ix_resource_usage_pipeline_time', 'pipeline_id', 'timestamp'),
        {'extend_existing': True}
    )

class Alert(BaseModel):
    __tablename__ = 'alerts'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id', ondelete='CASCADE'))
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

    pipeline = relationship('Pipeline', back_populates='alerts')
    acknowledger = relationship('User', foreign_keys=[acknowledged_by])
    resolver = relationship('User', foreign_keys=[resolved_by])

    __table_args__ = (
        Index('ix_alerts_status_severity', 'status', 'severity'),
        {'extend_existing': True}
    )

class AlertRule(BaseModel):
    __tablename__ = 'alert_rules'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id', ondelete='CASCADE'))
    name = Column(String(255))
    metric = Column(String(255))
    condition = Column(Enum('above', 'below', 'equals', name='alert_condition'))
    threshold = Column(Float)
    duration = Column(Integer)  # seconds
    severity = Column(Enum('info', 'warning', 'critical', name='rule_severity'))
    enabled = Column(Boolean, default=True)
    description = Column(Text)
    notification_channels = Column(JSONB)

    pipeline = relationship('Pipeline', back_populates='alert_rules')

    __table_args__ = (
        CheckConstraint('duration > 0', name='ck_duration_positive'),
        Index('ix_alert_rules_pipeline_metric', 'pipeline_id', 'metric'),
        {'extend_existing': True}
    )

class HealthCheck(BaseModel):
    __tablename__ = 'health_checks'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id', ondelete='CASCADE'))
    component = Column(String(255))
    status = Column(Enum('healthy', 'degraded', 'failing', name='health_status'))
    last_check = Column(DateTime)
    details = Column(JSONB)
    error = Column(Text)

    pipeline = relationship('Pipeline', back_populates='health_checks')

    __table_args__ = (
        Index('ix_health_checks_status', 'status'),
        Index('ix_health_checks_component', 'component'),
        {'extend_existing': True}
    )