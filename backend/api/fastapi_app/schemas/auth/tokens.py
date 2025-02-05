# schemas/auth/tokens.py
from marshmallow import Schema, fields, validate, ValidationError, EXCLUDE
from datetime import datetime

class TokenRequestSchema(Schema):
    """Schema for token requests"""
    token_type = fields.String(required=True, validate=validate.OneOf(['access', 'refresh']))
    client_id = fields.String(required=True)
    client_secret = fields.String(required=True, load_only=True)
    scope = fields.List(fields.String())

    class Meta:
        unknown = EXCLUDE

class TokenResponseSchema(Schema):
    """Schema for token responses"""
    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)
    token_type = fields.String(default='bearer')
    expires_in = fields.Integer()
    scope = fields.List(fields.String())
    issued_at = fields.DateTime(default=datetime.utcnow)

    class Meta:
        unknown = EXCLUDE
        ordered = True