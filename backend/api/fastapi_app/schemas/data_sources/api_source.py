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


class APISourceConfigSchema(StagingRequestSchema):
    """Schema for API source configuration and validation"""
    # API Endpoint Configuration
    base_url = fields.String(required=True)
    endpoints = fields.Dict(keys=fields.String(), values=fields.Dict())
    version = fields.String(allow_none=True)

    # Authentication Settings
    auth_type = fields.String(required=True, validate=OneOf([
        'basic', 'oauth2', 'api_key', 'bearer', 'custom'
    ]))
    auth_config = fields.Dict(required=True)
    refresh_token_url = fields.String(allow_none=True)

    # Request Configuration
    headers = fields.Dict(default=dict)
    default_params = fields.Dict(default=dict)
    timeout = fields.Integer(default=30)
    verify_ssl = fields.Boolean(default=True)

    # Rate Limiting
    rate_limit = fields.Dict(default=lambda: {
        'requests_per_second': 10,
        'burst_size': 20,
        'timeout': 30
    })

    # Retry Configuration
    retry_config = fields.Dict(default=lambda: {
        'max_retries': 3,
        'retry_delay': 1,
        'retry_on_status': [429, 500, 502, 503, 504]
    })

    # Response Processing
    response_format = fields.String(validate=OneOf(['json', 'xml', 'csv', 'text']))
    pagination_config = fields.Dict(allow_none=True)
    error_mapping = fields.Dict(allow_none=True)

    # Monitoring
    monitoring_config = fields.Dict(default=lambda: {
        'log_level': 'INFO',
        'metric_collection': True,
        'alert_on_error': True
    })

    @validates_schema
    def validate_auth_configuration(self, data: Dict[str, Any], **kwargs) -> None:
        required_auth_fields = {
            'basic': ['username', 'password'],
            'oauth2': ['client_id', 'client_secret', 'token_url'],
            'api_key': ['key', 'key_location'],
            'bearer': ['token'],
            'custom': ['auth_handler']
        }

        auth_type = data['auth_type']
        if auth_type in required_auth_fields:
            missing_fields = [
                field for field in required_auth_fields[auth_type]
                if field not in data['auth_config']
            ]
            if missing_fields:
                raise ValidationError(
                    f"Missing required authentication fields for {auth_type}: {missing_fields}"
                )

        if auth_type == 'oauth2' and 'refresh_token_url' not in data:
            raise ValidationError("refresh_token_url is required for OAuth2 authentication")