# schemas/auth/base.py
from marshmallow import Schema, fields, validate, ValidationError
from ..staging.base import StagingRequestSchema, StagingResponseSchema
from datetime import datetime

# schemas/auth/user.py
class UserProfileSchema(StagingResponseSchema):
    """Schema for user profile data"""
    email = fields.Email(dump_only=True)
    username = fields.String(dump_only=True)
    first_name = fields.String()
    last_name = fields.String()
    full_name = fields.String(dump_only=True)
    role = fields.String(dump_only=True)
    permissions = fields.List(fields.String(), dump_only=True)
    status = fields.String(validate=validate.OneOf([
        'active', 'inactive', 'suspended', 'pending'
    ]))
    email_verified = fields.Boolean(dump_only=True)
    profile_image = fields.String()
    phone_number = fields.String(validate=validate.Length(max=20))
    department = fields.String()
    timezone = fields.String()
    locale = fields.String()
    preferences = fields.Dict()
    metadata = fields.Dict()
    security_level = fields.Integer(validate=validate.Range(min=0, max=10))

class UpdateProfileRequestSchema(StagingResponseSchema):
    pass

class UpdateProfileResponseSchema(StagingResponseSchema):
    pass

