# schemas/data_sources/s3_source.py
from marshmallow import fields, validates_schema, ValidationError
from marshmallow.validate import OneOf
from typing import Dict, Any

from ..staging.base import StagingRequestSchema, StagingResponseSchema


class S3SourceRequestSchema(StagingRequestSchema):
    """Schema for S3 data source requests"""
    bucket = fields.String(required=True)
    region = fields.String(required=True)
    prefix = fields.String(allow_none=True)

    # Authentication
    access_key = fields.String(required=True, load_only=True)
    secret_key = fields.String(required=True, load_only=True)
    session_token = fields.String(load_only=True, allow_none=True)

    # Configuration
    encryption_config = fields.Dict(default=dict)
    storage_class = fields.String(validate=OneOf([
        'STANDARD', 'STANDARD_IA', 'ONEZONE_IA', 'GLACIER', 'DEEP_ARCHIVE'
    ]))
    transfer_config = fields.Dict(default=lambda: {
        'multipart_threshold': 8388608,  # 8MB
        'max_concurrency': 10,
        'multipart_chunksize': 8388608,
        'use_threads': True
    })

    versioning_enabled = fields.Boolean(default=False)
    lifecycle_rules = fields.List(fields.Dict(), default=list)

    @validates_schema
    def validate_config(self, data: Dict[str, Any], **kwargs) -> None:
        # Validate bucket naming rules
        if not 3 <= len(data['bucket']) <= 63:
            raise ValidationError('Bucket name must be between 3 and 63 characters')

        # Validate AWS regions
        valid_regions = ['us-east-1', 'us-west-1', 'eu-west-1', 'ap-southeast-1']
        if data['region'] not in valid_regions:
            raise ValidationError(f'Invalid AWS region: {data["region"]}')


class S3SourceResponseSchema(StagingResponseSchema):
    """Schema for S3 data source responses"""
    connection_status = fields.String(validate=OneOf(['connected', 'disconnected', 'error']))
    total_objects = fields.Integer()
    total_size = fields.Integer()  # bytes
    bucket_metrics = fields.Dict()
    last_sync = fields.DateTime(allow_none=True)
    versioning_status = fields.String(validate=OneOf(['Enabled', 'Suspended', 'Disabled']))
    replication_status = fields.Dict()
    transfer_stats = fields.Dict()


class S3UploadRequestSchema(StagingRequestSchema):
    bucket = fields.String(required=True)
    key = fields.String(required=True)
    content_type = fields.String(required=True)
    chunk_number = fields.Integer(required=True)
    total_chunks = fields.Integer(required=True)
    part_size = fields.Integer(required=True)
    total_size = fields.Integer(required=True)
    upload_id = fields.String()


class S3UploadResponseSchema(StagingResponseSchema):
    upload_id = fields.String()
    parts_uploaded = fields.Integer()
    bytes_transferred = fields.Integer()
    etag = fields.String()
    upload_status = fields.String(validate=OneOf(['initiated', 'in_progress', 'completed', 'failed']))
    presigned_url = fields.String()


class S3MetadataResponseSchema(StagingResponseSchema):
    bucket_info = fields.Dict()
    object_info = fields.Dict()
    storage_class = fields.String()
    encryption = fields.Dict()
    tags = fields.Dict()
    version_id = fields.String()
    preview_data = fields.List(fields.Dict())
