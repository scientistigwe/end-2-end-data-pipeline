from marshmallow import Schema, fields, validate, ValidationError, validates_schema


# Basic password validator pattern
def password_validator(password: str) -> bool:
    """Validate password meets minimum requirements"""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    # Add other password requirements if needed
    return True


class RegistrationRequestSchema(Schema):
    """Schema for registration requests"""
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=password_validator)
    confirm_password = fields.String(required=True)
    username = fields.String(required=True, validate=validate.Length(min=3, max=50))
    first_name = fields.String(required=True)
    last_name = fields.String(required=True)
    terms_accepted = fields.Boolean(required=True)

    # Optional fields
    timezone = fields.String(load_default='UTC')
    locale = fields.String(load_default='en')

    @validates_schema
    def validate_passwords(self, data, **kwargs):
        if data['password'] != data['confirm_password']:
            raise ValidationError('Passwords must match')


from marshmallow import Schema, fields, validate, ValidationError, validates_schema
from uuid import UUID

class UserProfileSchema(Schema):
    """Schema for user profile data"""
    id = fields.UUID(dump_only=True)
    email = fields.Email(dump_only=True)
    username = fields.String(dump_only=True)
    first_name = fields.String(dump_only=True)
    last_name = fields.String(dump_only=True)
    status = fields.String(dump_only=True)
    role = fields.String(dump_only=True)
    is_active = fields.Boolean(dump_only=True)
    email_verified = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    last_login = fields.DateTime(dump_only=True)
    profile_image = fields.String(dump_only=True)
    department = fields.String(dump_only=True)
    timezone = fields.String(dump_only=True)
    locale = fields.String(dump_only=True)
    preferences = fields.Dict(dump_only=True)

class RegistrationResponseSchema(Schema):
    """Schema for registration responses"""
    user = fields.Nested(UserProfileSchema)
    verification_email_sent = fields.Boolean()