# schemas/auth/base.py
from marshmallow import Schema, fields, validate, ValidationError
from ..staging.base import StagingRequestSchema, StagingResponseSchema
from datetime import datetime


# schemas/auth/session.py
class SessionRequestSchema(StagingRequestSchema):
    """Schema for session management requests"""
    session_id = fields.UUID(required=True)
    action = fields.String(validate=validate.OneOf(['extend', 'terminate', 'refresh']))
    device_info = fields.Dict()


class SessionResponseSchema(StagingResponseSchema):
    """Schema for session management responses"""
    session_id = fields.UUID()
    expires_at = fields.DateTime()
    last_accessed = fields.DateTime()
    active_sessions = fields.Integer()

