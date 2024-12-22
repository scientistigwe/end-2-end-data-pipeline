# schemas/pipeline.py
from marshmallow import Schema, fields, validate
from .base import BaseRequestSchema, BaseResponseSchema

class PipelineRequestSchema(BaseRequestSchema):
    """Schema for creating a new pipeline."""
    name = fields.String(required=True)
    description = fields.String()
    mode = fields.String(validate=validate.OneOf(['development', 'staging', 'production']))
    source_id = fields.UUID(required=True)
    target_id = fields.UUID()
    config = fields.Dict()
    schedule_enabled = fields.Boolean(default=False)
    schedule_cron = fields.String()
    schedule_timezone = fields.String()

class PipelineResponseSchema(BaseResponseSchema):
    """Schema for pipeline response."""
    name = fields.String()
    description = fields.String()
    status = fields.String(validate=validate.OneOf([
        'idle', 'running', 'paused', 'completed', 'failed', 'cancelled'
    ]))
    mode = fields.String()
    source_id = fields.UUID()
    target_id = fields.UUID()
    config = fields.Dict()
    progress = fields.Float()
    error = fields.String()
    last_run = fields.DateTime()
    next_run = fields.DateTime()
    version = fields.Integer()
    total_runs = fields.Integer()
    successful_runs = fields.Integer()
    average_duration = fields.Float()

class PipelineListResponseSchema(BaseResponseSchema):
    """Schema for list of pipelines response."""
    pipelines = fields.List(fields.Nested(PipelineResponseSchema))
    total_count = fields.Integer()
    active_count = fields.Integer()

class PipelineUpdateRequestSchema(BaseRequestSchema):
    """Schema for updating a pipeline."""
    name = fields.String()
    description = fields.String()
    config = fields.Dict()
    schedule_enabled = fields.Boolean()
    schedule_cron = fields.String()
    schedule_timezone = fields.String()

class PipelineStartRequestSchema(BaseRequestSchema):
    """Schema for starting a pipeline."""
    source_type = fields.String(required=True, validate=validate.OneOf(['file', 'api', 'stream']))
    config = fields.Dict(required=True)
    parameters = fields.Dict(required=False)

class PipelineStartResponseSchema(BaseResponseSchema):
    """Schema for pipeline start response."""
    run_id = fields.UUID()
    status = fields.String()
    start_time = fields.DateTime()

class PipelineStatusResponseSchema(BaseResponseSchema):
    """Schema for pipeline status response."""
    status = fields.String(validate=validate.OneOf([
        'idle', 'running', 'paused', 'completed', 'failed', 'cancelled'
    ]))
    progress = fields.Float()
    current_step = fields.String()
    start_time = fields.DateTime()
    estimated_completion = fields.DateTime()

class PipelineLogsRequestSchema(BaseRequestSchema):
    """Schema for pipeline logs request."""
    start_time = fields.DateTime()
    end_time = fields.DateTime()
    level = fields.String(validate=validate.OneOf(['INFO', 'WARNING', 'ERROR']))
    limit = fields.Integer()

class PipelineLogsResponseSchema(BaseResponseSchema):
    """Schema for pipeline logs response."""
    logs = fields.List(fields.Dict(keys=fields.String(), values=fields.Raw()))
    start_time = fields.DateTime()
    end_time = fields.DateTime()

class PipelineMetricsResponseSchema(BaseResponseSchema):
    """Schema for pipeline metrics response."""
    total_runs = fields.Integer()
    successful_runs = fields.Integer()
    failed_runs = fields.Integer()
    average_duration = fields.Float()
    success_rate = fields.Float()
    last_run_status = fields.String()
    performance_metrics = fields.Dict()

class PipelineConfigValidationRequestSchema(BaseRequestSchema):
    """Schema for pipeline configuration validation request."""
    config = fields.Dict(required=True)
    source_type = fields.String(required=True)
    target_type = fields.String()
    mode = fields.String()

class PipelineConfigValidationResponseSchema(BaseResponseSchema):
    """Schema for pipeline configuration validation response."""
    is_valid = fields.Boolean()
    errors = fields.List(fields.String())
    warnings = fields.List(fields.String())
    suggestions = fields.List(fields.String())