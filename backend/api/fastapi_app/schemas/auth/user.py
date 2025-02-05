# schemas/auth/user.py

from marshmallow import Schema, fields, validate, ValidationError, EXCLUDE
from .base import name_validator

class UserProfileSchema(Schema):
    """Schema for user profile data"""
    id = fields.String(required=True)
    email = fields.Email(dump_only=True)
    username = fields.String(dump_only=True)
    first_name = fields.String(validate=name_validator)
    last_name = fields.String(validate=name_validator)
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

    class Meta:
        ordered = True
        unknown = EXCLUDE

class UpdateProfileRequestSchema(Schema):
    pass

class UpdateProfileResponseSchema(Schema):
    pass

