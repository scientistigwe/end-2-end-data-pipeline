# schemas/data_source.py
from marshmallow import Schema, fields, validate, validates_schema, ValidationError
from .base import BaseRequestSchema, BaseResponseSchema
from .data_sources.file_source import FileSourceConfigSchema
from .data_sources.database_source import DatabaseSourceConfigSchema
from .data_sources.api_source import APISourceConfigSchema
from .data_sources.s3_source import S3SourceConfigSchema
from .data_sources.stream_source import StreamSourceConfigSchema

class DataSourceRequestSchema(BaseRequestSchema):
    """High-level schema for data source creation/update"""
    name = fields.String(required=True)
    type = fields.String(required=True, validate=validate.OneOf([
        'file', 'database', 'api', 's3', 'stream'
    ]))
    description = fields.String()
    
    # Source-specific configuration
    file_config = fields.Nested(FileSourceConfigSchema, required=False)
    database_config = fields.Nested(DatabaseSourceConfigSchema, required=False)
    api_config = fields.Nested(APISourceConfigSchema, required=False)
    s3_config = fields.Nested(S3SourceConfigSchema, required=False)
    stream_config = fields.Nested(StreamSourceConfigSchema, required=False)
    
    # Common settings
    refresh_interval = fields.Integer()
    is_active = fields.Boolean(default=True)

    @validates_schema
    def validate_config(self, data, **kwargs):
        """Ensure the correct config is provided for the source type"""
        source_type = data.get('type')
        config_field = f'{source_type}_config'
        
        if source_type and not data.get(config_field):
            raise ValidationError(
                f'Configuration for {source_type} source is required'
            )

class DataSourceResponseSchema(BaseResponseSchema):
    """High-level schema for data source response"""
    name = fields.String()
    type = fields.String()
    description = fields.String()
    status = fields.String(validate=validate.OneOf(['active', 'inactive', 'error']))
    meta_data = fields.Dict()
    last_sync = fields.DateTime()
    error = fields.String()
    
    # Source-specific status and metadata
    source_config = fields.Dict()  # The active configuration
    connection_status = fields.Dict()  # Current connection status
    performance_metrics = fields.Dict()  # Performance-related metrics