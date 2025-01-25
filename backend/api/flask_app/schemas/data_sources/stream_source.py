# schemas/data_sources/stream_source.py
from marshmallow import fields, validates_schema, ValidationError
from marshmallow.validate import OneOf
from typing import Dict, Any

from ..staging.base import StagingRequestSchema, StagingResponseSchema


class StreamSourceRequestSchema(StagingRequestSchema):
    """Schema for stream data source requests"""
    stream_type = fields.String(required=True, validate=OneOf(['kafka', 'kinesis', 'rabbitmq', 'pubsub']))
    connection_config = fields.Dict(required=True)

    # Stream Processing
    batch_size = fields.Integer(default=100)
    processing_timeout = fields.Integer(default=30)  # seconds
    error_handling = fields.Dict(default=dict)

    # Performance
    concurrency = fields.Integer(default=1)
    rate_limiting = fields.Dict(default=dict)
    checkpoint_interval = fields.Integer(default=60)  # seconds

    @validates_schema
    def validate_connection_config(self, data: Dict[str, Any], **kwargs) -> None:
        required_fields = {
            'kafka': ['bootstrap_servers', 'topic'],
            'kinesis': ['stream_name', 'region'],
            'rabbitmq': ['host', 'queue'],
            'pubsub': ['project_id', 'subscription_name']
        }

        for field in required_fields[data['stream_type']]:
            if field not in data['connection_config']:
                raise ValidationError(f'{field} required for {data["stream_type"]} configuration')


class StreamSourceResponseSchema(StagingResponseSchema):
    """Schema for stream data source responses"""
    stream_status = fields.String(validate=OneOf(['active', 'paused', 'error']))
    current_throughput = fields.Float()  # messages/second
    lag = fields.Integer()  # message backlog
    processing_metrics = fields.Dict()
    error_count = fields.Integer()
    last_checkpoint = fields.DateTime(allow_none=True)


class StreamUploadRequestSchema(StagingRequestSchema):
    stream_name = fields.String(required=True)
    partition_key = fields.String(required=True)
    sequence_number = fields.String()
    data = fields.Dict(required=True)
    encoding = fields.String(default='utf-8')


class StreamUploadResponseSchema(StagingResponseSchema):
    sequence_number = fields.String()
    shard_id = fields.String()
    timestamp = fields.DateTime()
    partition_key = fields.String()
    bytes_processed = fields.Integer()
    upload_status = fields.String(validate=OneOf(['pending', 'processing', 'delivered', 'failed']))


class StreamMetadataResponseSchema(StagingResponseSchema):
    stream_info = fields.Dict()
    shard_info = fields.Dict()
    throughput = fields.Dict()
    retention_period = fields.Integer()
    encryption_type = fields.String()
    preview_data = fields.List(fields.Dict())