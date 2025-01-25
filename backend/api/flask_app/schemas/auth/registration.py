# schemas/auth/base.py
from marshmallow import Schema, fields, validate, ValidationError, validates_schema
from ..auth.base import password_validator, name_validator
from .user import UserProfileSchema
from .tokens import TokenResponseSchema
from ..staging.base import StagingRequestSchema, StagingResponseSchema
from datetime import datetime

# schemas/auth/registration.py
class RegistrationRequestSchema(StagingRequestSchema):
    """Schema for registration requests"""
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=password_validator, load_only=True)
    confirm_password = fields.String(required=True, load_only=True)
    username = fields.String(required=True, validate=validate.Length(min=3, max=50))
    first_name = fields.String(required=True, validate=name_validator)
    last_name = fields.String(required=True, validate=name_validator)
    phone_number = fields.String(validate=validate.Length(max=20))
    department = fields.String(validate=validate.Length(max=100))
    timezone = fields.String(load_default='UTC')
    locale = fields.String(load_default='en')
    terms_accepted = fields.Boolean(required=True)
    metadata = fields.Dict(load_default=dict)

    @validates_schema
    def validate_passwords(self, data, **kwargs):
        if data['password'] != data['confirm_password']:
            raise ValidationError('Passwords must match')


class RegistrationResponseSchema(StagingResponseSchema):
    """Schema for registration responses"""
    user = fields.Nested(UserProfileSchema)
    tokens = fields.Nested(TokenResponseSchema)
    verification_email_sent = fields.Boolean()
    next_steps = fields.List(fields.String())


