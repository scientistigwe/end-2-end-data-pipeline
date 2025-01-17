# schemas/data_sources/api_source.py
from marshmallow import Schema, fields, validate
from ..base import BaseRequestSchema, BaseResponseSchema

class APISourceConfigSchema(BaseRequestSchema):
    base_url = fields.String(required=True)
    auth_type = fields.String(required=True, validate=validate.OneOf(['basic', 'oauth', 'api_key']))
    auth_config = fields.Dict(required=True)
    rate_limit = fields.Integer()
    timeout = fields.Integer()
    headers = fields.Dict()
    retry_config = fields.Dict()
    webhook_url = fields.String()
    webhook_secret = fields.String(load_only=True)

class APISourceResponseSchema(BaseResponseSchema):
    status = fields.String(validate=validate.OneOf(['active', 'inactive', 'error']))
    last_response_time = fields.Integer()  # in milliseconds
    success_rate = fields.Float()