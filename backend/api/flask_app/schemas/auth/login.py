# schemas/auth/base.py
from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime
from .user import UserProfileSchema
from .tokens import TokenResponseSchema
from ..staging.base import StagingRequestSchema, StagingResponseSchema


# schemas/auth/login.py
class LoginRequestSchema(StagingRequestSchema):
    """Schema for login requests"""
    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)
    remember_me = fields.Boolean(load_default=False)
    device_info = fields.Dict(load_default=dict)
    mfa_code = fields.String(load_only=True)


class LoginResponseSchema(StagingResponseSchema):
    """Schema for login responses"""
    user = fields.Nested(UserProfileSchema)
    tokens = fields.Nested(TokenResponseSchema)
    mfa_required = fields.Boolean(default=False)
    session_expires = fields.DateTime()
    permitted_actions = fields.List(fields.String())

