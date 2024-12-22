# app/schemas/auth.py
from marshmallow import Schema, fields, validate, ValidationError

# Login schemas
class LoginRequestSchema(Schema):
    """Schema for login request validation."""
    email = fields.Email(required=True)
    password = fields.String(required=True)

class LoginResponseSchema(Schema):
    """Schema for login response."""
    tokens = fields.Nested(lambda: TokenResponseSchema())
    user = fields.Nested(lambda: UserProfileResponseSchema())

# Register schemas
class RegisterRequestSchema(Schema):
    """Schema for user registration validation."""
    email = fields.Email(required=True)
    password = fields.String(
        required=True,
        validate=validate.Length(min=8)
    )
    full_name = fields.String(required=True)
    role = fields.String(validate=validate.OneOf(['user', 'admin']), default='user')

class RegisterResponseSchema(Schema):
    """Schema for registration response."""
    message = fields.String()
    user = fields.Nested(lambda: UserProfileResponseSchema())

# Token schemas
class TokenResponseSchema(Schema):
    """Schema for token response serialization."""
    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)
    token_type = fields.String(default='bearer')

# Password reset schemas
class PasswordResetRequestSchema(Schema):
    """Schema for password reset validation."""
    token = fields.String(required=True)
    new_password = fields.String(
        required=True,
        validate=validate.Length(min=8)
    )

class PasswordResetResponseSchema(Schema):
    """Schema for password reset response."""
    message = fields.String()
    success = fields.Boolean()

# Email verification schemas
class EmailVerificationRequestSchema(Schema):
    """Schema for email verification validation."""
    token = fields.String(required=True)

class EmailVerificationResponseSchema(Schema):
    """Schema for email verification response."""
    message = fields.String()
    success = fields.Boolean()

# Change password schemas
class ChangePasswordRequestSchema(Schema):
    """Schema for password change validation."""
    current_password = fields.String(required=True)
    new_password = fields.String(
        required=True,
        validate=validate.Length(min=8)
    )

class ChangePasswordResponseSchema(Schema):
    """Schema for password change response."""
    message = fields.String()
    success = fields.Boolean()

# User profile schemas
class UserProfileResponseSchema(Schema):
    """Schema for user profile response."""
    id = fields.UUID(dump_only=True)
    email = fields.Email(dump_only=True)
    full_name = fields.String()
    role = fields.String(dump_only=True)
    status = fields.String(dump_only=True)
    last_login = fields.DateTime(dump_only=True)
    email_verified = fields.Boolean(dump_only=True)
    profile_image = fields.String()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class UserProfileUpdateRequestSchema(Schema):
    """Schema for user profile update validation."""
    full_name = fields.String()
    profile_image = fields.String()