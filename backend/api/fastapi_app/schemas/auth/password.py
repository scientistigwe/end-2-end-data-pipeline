# schemas/auth/base.py
from marshmallow import Schema, fields, validate, ValidationError, validates_schema
from ..auth.base import password_validator, name_validator
from ..staging.base import StagingRequestSchema, StagingResponseSchema
from datetime import datetime

# schemas/auth/password.py
class PasswordResetRequestSchema(StagingRequestSchema):
    """Schema for password reset requests"""
    token = fields.String(required=True)
    email = fields.Email(required=True)
    new_password = fields.String(required=True, validate=password_validator)
    confirm_password = fields.String(required=True)

    @validates_schema
    def validate_passwords(self, data, **kwargs):
        if data['new_password'] != data['confirm_password']:
            raise ValidationError('Passwords must match')


class PasswordResetResponseSchema(StagingResponseSchema):
    """Schema for password reset responses"""
    reset_at = fields.DateTime()
    requires_reverification = fields.Boolean()


class ChangePasswordRequestSchema(StagingRequestSchema):
    """Schema for password change requests"""
    current_password = fields.String(required=True)
    new_password = fields.String(required=True, validate=password_validator)
    confirm_password = fields.String(required=True)

    @validates_schema
    def validate_passwords(self, data, **kwargs):
        if data['new_password'] == data['current_password']:
            raise ValidationError('New password must be different')
        if data['new_password'] != data['confirm_password']:
            raise ValidationError('Passwords must match')


class ChangePasswordResponseSchema(StagingResponseSchema):
    """Schema for password change responses"""
    changed_at = fields.DateTime()
    requires_relogin = fields.Boolean()
