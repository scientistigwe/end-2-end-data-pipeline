# schemas/auth/base.py
from marshmallow import Schema, fields, validate, ValidationError
from .user import UserProfileSchema
from ..staging.base import StagingRequestSchema, StagingResponseSchema
from datetime import datetime


# schemas/auth/verification.py
class EmailVerificationRequestSchema(StagingRequestSchema):
    """Schema for email verification"""
    token = fields.String(required=True)
    email = fields.Email(required=True)


class EmailVerificationResponseSchema(StagingResponseSchema):
    """Schema for email verification responses"""
    verified_at = fields.DateTime()
    user = fields.Nested(UserProfileSchema)

