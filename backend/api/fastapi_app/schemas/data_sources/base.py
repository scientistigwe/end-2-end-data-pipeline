# schemas/data_sources/base.py
from marshmallow import fields, validates_schema, ValidationError
from marshmallow.validate import OneOf
from typing import Dict, Any

from .api_source import APISourceRequestSchema
from .database_source import DatabaseSourceRequestSchema
from .file_source import FileSourceRequestSchema
from .stream_source import StreamSourceRequestSchema
from ..staging.base import StagingRequestSchema
from .s3_source import S3SourceRequestSchema


class DataSourceSchema(StagingRequestSchema):
    """Unified schema for all data sources"""
    source_type = fields.String(required=True, validate=OneOf(['api', 'database', 'file', 'stream', 'S3']))
    name = fields.String(required=True)
    description = fields.String(allow_none=True)

    # Type-specific configurations
    api_config = fields.Nested(APISourceRequestSchema, allow_none=True)
    database_config = fields.Nested(DatabaseSourceRequestSchema, allow_none=True)
    file_config = fields.Nested(FileSourceRequestSchema, allow_none=True)
    stream_config = fields.Nested(StreamSourceRequestSchema, allow_none=True)
    s3_config = fields.Nested(S3SourceRequestSchema, allow_none=True)

    @validates_schema
    def validate_config_presence(self, data: Dict[str, Any], **kwargs) -> None:
        config_field = f"{data['source_type']}_config"
        if not data.get(config_field):
            raise ValidationError(f"Configuration required for {data['source_type']} source type")