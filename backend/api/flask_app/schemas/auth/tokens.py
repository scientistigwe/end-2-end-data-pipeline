# schemas/auth/base.py
from marshmallow import Schema, fields, validate, ValidationError
from ..staging.base import StagingRequestSchema, StagingResponseSchema
from datetime import datetime


# schemas/auth/tokens.py
class TokenRequestSchema(StagingRequestSchema):
    """Schema for token requests"""
    token_type = fields.String(required=True, validate=validate.OneOf(['access', 'refresh']))
    client_id = fields.String(required=True)
    client_secret = fields.String(required=True, load_only=True)
    scope = fields.List(fields.String())


class TokenResponseSchema(StagingResponseSchema):
    """Schema for token responses"""
    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)
    token_type = fields.String(default='bearer')
    expires_in = fields.Integer()
    scope = fields.List(fields.String())
    issued_at = fields.DateTime(default=datetime.utcnow)

