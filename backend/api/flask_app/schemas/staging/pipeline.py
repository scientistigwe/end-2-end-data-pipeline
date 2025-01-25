# schemas/pipeline.py
from marshmallow import Schema, fields, validates_schema, ValidationError
from marshmallow.validate import OneOf, Length
from marshmallow_enum import EnumField
from datetime import datetime
from typing import Dict, Any

from core.messaging.event_types import (
    ComponentType,
    ProcessingStage,
    ProcessingStatus
)
from core.messaging.event_types import ReportSectionType


class BasePipelineSchema(Schema):
    """Foundational pipeline schema with core attributes"""
    id = fields.String(required=True)
    name = fields.String(required=True, validate=Length(min=3, max=100))
    description = fields.String(allow_none=True)

    owner_id = fields.String(required=True)
    status = EnumField(ProcessingStatus, by_value=True, default=ProcessingStatus.PENDING)

    created_at = fields.DateTime(default=datetime.utcnow)
    updated_at = fields.DateTime(default=datetime.utcnow)


class PipelineRequestSchema(BasePipelineSchema):
    """Schema for creating or updating pipeline configurations"""
    source_configs = fields.Dict(required=True)
    destination_configs = fields.Dict(required=True)

    pipeline_type = fields.String(required=True)
    execution_mode = fields.String(validate=OneOf(['sequential', 'parallel', 'distributed']))

    max_retries = fields.Integer(validate=lambda n: 0 <= n <= 10, default=3)
    retry_strategy = fields.String(validate=OneOf(['exponential', 'linear', 'fixed']))

    @validates_schema
    def validate_pipeline_config(self, data: Dict[str, Any], **kwargs):
        if not data.get('source_configs'):
            raise ValidationError('Source configuration is required')
        if not data.get('destination_configs'):
            raise ValidationError('Destination configuration is required')


class PipelineStatusSchema(BasePipelineSchema):
    """Comprehensive pipeline status schema"""
    current_stage = EnumField(ProcessingStage, by_value=True)
    runtime_status = fields.Dict(allow_none=True)

    stages_completed = fields.List(fields.String())
    stage_metrics = fields.Dict()
    error_details = fields.Dict(allow_none=True)


class PipelineLogsSchema(Schema):
    """Schema for filtering pipeline logs"""
    start_time = fields.DateTime(allow_none=True)
    end_time = fields.DateTime(allow_none=True)
    log_level = fields.String(validate=OneOf(['INFO', 'WARNING', 'ERROR', 'DEBUG']))
    limit = fields.Integer(validate=lambda n: 1 <= n <= 1000, default=100)


class PipelineMetricsSchema(Schema):
    """Performance and resource utilization metrics"""
    processing_time = fields.Float()
    cpu_usage = fields.Float()
    memory_usage = fields.Float()
    records_processed = fields.Integer()
    error_rate = fields.Float()


class PipelineResponseSchema(Schema):
    """
    Comprehensive schema for pipeline response with detailed metadata
    """
    id = fields.String(required=True)
    name = fields.String(required=True)
    description = fields.String(allow_none=True)

    # Status and Lifecycle Tracking
    status = EnumField(ProcessingStatus, by_value=True)
    current_stage = EnumField(ProcessingStage, by_value=True, allow_none=True)

    # Configuration Details
    source_type = fields.String(required=True)
    destination_type = fields.String(required=True)

    # Execution Metadata
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    started_at = fields.DateTime(allow_none=True)
    completed_at = fields.DateTime(allow_none=True)

    # Performance and Resource Tracking
    execution_time = fields.Float(allow_none=True)
    records_processed = fields.Integer(default=0)

    # Error Handling
    error_count = fields.Integer(default=0)
    last_error = fields.Dict(allow_none=True)

    # Runtime Context
    runtime_status = fields.Dict(allow_none=True)
    configuration = fields.Dict()


class PipelineListResponseSchema(Schema):
    """
    Schema for paginated pipeline list response
    """
    pipelines = fields.List(fields.Nested(PipelineResponseSchema))
    total_count = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()


class PipelineStatusResponseSchema(Schema):
    """
    Detailed pipeline status response schema
    """
    id = fields.String(required=True)
    status = EnumField(ProcessingStatus, by_value=True)
    current_stage = EnumField(ProcessingStage, by_value=True, allow_none=True)

    stage_progress = fields.Dict()
    runtime_details = fields.Dict(allow_none=True)

    error_details = fields.Dict(allow_none=True)
    warnings = fields.List(fields.String())


class PipelineLogsResponseSchema(Schema):
    """
    Response schema for pipeline execution logs
    """
    logs = fields.List(fields.Dict())
    total_log_count = fields.Integer()
    filtered_log_count = fields.Integer()


class PipelineMetricsResponseSchema(Schema):
    """
    Comprehensive pipeline performance metrics
    """
    processing_duration = fields.Float()
    records_processed = fields.Integer()

    # Resource Utilization
    cpu_usage = fields.Float()
    memory_usage = fields.Float()

    # Performance Indicators
    throughput = fields.Float()
    error_rate = fields.Float()

    # Stage-specific Metrics
    stage_metrics = fields.Dict()

