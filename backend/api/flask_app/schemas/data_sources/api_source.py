# schemas/data_sources/api_source.py
from marshmallow import fields, validates_schema, ValidationError
from marshmallow.validate import OneOf
from typing import Dict, Any

from ..staging.base import StagingRequestSchema, StagingResponseSchema


class APISourceRequestSchema(StagingRequestSchema):
    """Schema for API data source requests"""
    base_url = fields.String(required=True)
    auth_type = fields.String(required=True, validate=OneOf(['basic', 'oauth', 'api_key', 'bearer']))
    auth_config = fields.Dict(required=True)

    # API Configuration
    headers = fields.Dict(default=dict)
    rate_limit = fields.Integer()
    timeout = fields.Integer(default=30)
    retry_config = fields.Dict(default=dict)

    # Webhook Configuration
    webhook_url = fields.String(allow_none=True)
    webhook_secret = fields.String(load_only=True, allow_none=True)

    @validates_schema
    def validate_auth_config(self, data: Dict[str, Any], **kwargs) -> None:
        required_fields = {
            'basic': ['username', 'password'],
            'oauth': ['client_id', 'client_secret'],
            'api_key': ['key', 'header_name'],
            'bearer': ['token']
        }

        if data['auth_type'] in required_fields:
            for field in required_fields[data['auth_type']]:
                if field not in data['auth_config']:
                    raise ValidationError(f'{field} required for {data["auth_type"]} authentication')


class APISourceResponseSchema(StagingResponseSchema):
    """Schema for API data source responses"""
    connection_status = fields.String(validate=OneOf(['connected', 'disconnected', 'error']))
    response_time = fields.Integer()  # milliseconds
    last_successful_request = fields.DateTime(allow_none=True)
    error_rate = fields.Float(validate=lambda n: 0 <= n <= 1)
    rate_limit_remaining = fields.Integer(allow_none=True)

# schemas/data_sources/api_source.py
class APIUploadRequestSchema(StagingRequestSchema):
   endpoint = fields.String(required=True)
   method = fields.String(validate=OneOf(['GET', 'POST', 'PUT']))
   headers = fields.Dict()
   payload = fields.Dict()
   stream = fields.Boolean(default=False)

class APIUploadResponseSchema(StagingResponseSchema):
   response_code = fields.Integer()
   response_headers = fields.Dict()
   data_size = fields.Integer()
   processing_time = fields.Float()

class APIMetadataResponseSchema(StagingResponseSchema):
   endpoint_info = fields.Dict()
   rate_limits = fields.Dict()
   data_format = fields.String()
   schema = fields.Dict()
   preview_data = fields.List(fields.Dict())