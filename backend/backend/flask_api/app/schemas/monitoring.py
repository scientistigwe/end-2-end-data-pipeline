# schemas/monitoring.py
from marshmallow import Schema, fields, validate
from .base import BaseRequestSchema, BaseResponseSchema

class MetricsRequestSchema(BaseRequestSchema):
    """Schema for metrics request."""
    start_time = fields.DateTime()
    end_time = fields.DateTime()
    interval = fields.String()
    metric_types = fields.List(fields.String())
    aggregation = fields.String()

class MetricsResponseSchema(BaseResponseSchema):
    """Schema for metrics response."""
    metrics = fields.List(fields.Dict(
        name=fields.String(),
        value=fields.Float(),
        timestamp=fields.DateTime(),
        labels=fields.Dict()
    ))
    summary = fields.Dict()

class HealthStatusResponseSchema(BaseResponseSchema):
    """Schema for health status response."""
    status = fields.String(validate=validate.OneOf(['healthy', 'degraded', 'failing']))
    components = fields.Dict(keys=fields.String(), values=fields.Dict())
    last_check = fields.DateTime()
    details = fields.Dict()

class PerformanceMetricsResponseSchema(BaseResponseSchema):
    """Schema for performance metrics response."""
    cpu_usage = fields.Float()
    memory_usage = fields.Float()
    disk_usage = fields.Float()
    network_io = fields.Dict()
    response_times = fields.Dict()

class MonitoringMetricRequestSchema(BaseRequestSchema):
    """Schema for monitoring metric request."""
    pipeline_id = fields.UUID(required=True)
    name = fields.String(required=True)
    value = fields.Float(required=True)
    labels = fields.Dict(required=False)
    type = fields.String(validate=validate.OneOf(['gauge', 'counter', 'histogram']))
    unit = fields.String(required=False)

class AlertConfigRequestSchema(BaseRequestSchema):
    """Schema for alert configuration request."""
    pipeline_id = fields.UUID(required=True)
    rules = fields.List(fields.Dict(
        metric=fields.String(required=True),
        condition=fields.String(required=True),
        threshold=fields.Float(required=True),
        duration=fields.Integer(),
        severity=fields.String()
    ))
    notifications = fields.Dict()

class AlertConfigResponseSchema(BaseResponseSchema):
    """Schema for alert configuration response."""
    config = fields.Dict()
    active_rules = fields.Integer()
    last_updated = fields.DateTime()

class AlertRequestSchema(BaseRequestSchema):
    """Schema for alert request."""
    pipeline_id = fields.UUID(required=True)
    type = fields.String(required=True)
    severity = fields.String(validate=validate.OneOf(['info', 'warning', 'critical']))
    message = fields.String(required=True)

class AlertResponseSchema(BaseResponseSchema):
    """Schema for alert response."""
    status = fields.String(validate=validate.OneOf(['active', 'acknowledged', 'resolved']))
    meta_data = fields.Dict()
    acknowledged_by = fields.UUID()
    acknowledged_at = fields.DateTime()
    resolved_by = fields.UUID()
    resolved_at = fields.DateTime()

class AlertHistoryResponseSchema(BaseResponseSchema):
    """Schema for alert history response."""
    history = fields.List(fields.Dict(
        alert_id=fields.UUID(),
        type=fields.String(),
        severity=fields.String(),
        status=fields.String(),
        created_at=fields.DateTime(),
        resolved_at=fields.DateTime()
    ))
    summary = fields.Dict()

class ResourceUsageResponseSchema(BaseResponseSchema):
    """Schema for resource usage response."""
    cpu_usage = fields.Float()
    memory_usage = fields.Float()
    disk_usage = fields.Float()
    network_in = fields.Float()
    network_out = fields.Float()
    meta_data = fields.Dict()

class AggregatedMetricsResponseSchema(BaseResponseSchema):
    """Schema for aggregated metrics response."""
    metrics = fields.Dict(
        keys=fields.String(),
        values=fields.Dict(
            current=fields.Float(),
            average=fields.Float(),
            min=fields.Float(),
            max=fields.Float(),
            percentiles=fields.Dict()
        )
    )
    period = fields.String()