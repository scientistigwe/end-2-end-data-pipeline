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


class StreamSourceConfigSchema(StagingRequestSchema):
    """Schema for stream source configuration and validation"""
    # Stream Settings
    stream_type = fields.String(required=True, validate=OneOf([
        'kafka', 'kinesis', 'rabbitmq', 'pubsub'
    ]))
    connection_config = fields.Dict(required=True)

    # Consumer Settings
    consumer_config = fields.Dict(default=lambda: {
        'group_id': None,
        'auto_offset_reset': 'latest',
        'enable_auto_commit': True,
        'auto_commit_interval_ms': 5000
    })

    # Processing Settings
    processing_config = fields.Dict(default=lambda: {
        'batch_size': 100,
        'processing_timeout': 30,
        'max_retries': 3,
        'dead_letter_queue': None
    })

    # Performance Settings
    performance_config = fields.Dict(default=lambda: {
        'concurrency': 1,
        'max_poll_records': 500,
        'poll_timeout_ms': 1000,
        'max_partition_fetch_bytes': 1048576
    })

    # Error Handling
    error_handling = fields.Dict(default=lambda: {
        'retry_backoff_ms': 500,
        'retry_on_error': True,
        'skip_invalid_records': False
    })

    # Monitoring Settings
    monitoring_config = fields.Dict(default=lambda: {
        'enable_metrics': True,
        'metric_interval': 60,
        'lag_threshold': 1000
    })

    # Checkpoint Settings
    checkpoint_config = fields.Dict(default=lambda: {
        'checkpoint_interval': 60,
        'checkpoint_store': 'memory',
        'store_config': {}
    })

    @validates_schema
    def validate_stream_config(self, data: Dict[str, Any], **kwargs) -> None:
        required_fields = {
            'kafka': ['bootstrap_servers', 'topics'],
            'kinesis': ['stream_name', 'region'],
            'rabbitmq': ['host', 'queue_name'],
            'pubsub': ['project_id', 'subscription_name']
        }

        stream_type = data['stream_type']
        if stream_type in required_fields:
            missing_fields = [
                field for field in required_fields[stream_type]
                if field not in data['connection_config']
            ]
            if missing_fields:
                raise ValidationError(
                    f"Missing required fields for {stream_type}: {missing_fields}"
                )

        # Validate consumer group for Kafka
        if stream_type == 'kafka' and not data['consumer_config'].get('group_id'):
            raise ValidationError("Consumer group ID is required for Kafka")