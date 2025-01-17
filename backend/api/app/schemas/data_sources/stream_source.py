# schemas/data_sources/stream_source.py
from marshmallow import Schema, fields, validate
from ..base import BaseRequestSchema, BaseResponseSchema

class StreamSourceConfigSchema(BaseRequestSchema):
    """Schema for stream source configuration"""
    stream_type = fields.String(required=True, validate=validate.OneOf(['kafka', 'kinesis', 'rabbitmq', 'pubsub']))
    endpoint = fields.String(required=True)
    partitions = fields.Integer()
    batch_size = fields.Integer()
    processing_config = fields.Dict(required=True)
    error_handling = fields.Dict()
    checkpoint_config = fields.Dict()
    scaling_config = fields.Dict()
    
    # Authentication
    auth_config = fields.Dict()
    
    # Performance settings
    max_batch_size = fields.Integer()
    processing_timeout = fields.Integer()
    retry_policy = fields.Dict()

class StreamSourceResponseSchema(BaseResponseSchema):
    """Schema for stream source status and metrics"""
    status = fields.String(validate=validate.OneOf(['active', 'paused', 'error']))
    throughput = fields.Float()  # messages per second
    lag = fields.Integer()  # message backlog
    partition_count = fields.Integer()
    error_rate = fields.Float()
    last_checkpoint = fields.DateTime()
    metrics = fields.Dict()