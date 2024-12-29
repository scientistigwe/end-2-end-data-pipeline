# app/schemas/auth.py
from marshmallow import Schema, fields, validate, ValidationError, post_load


# Token schemas
class TokenResponseSchema(Schema):
    """Schema for token response serialization."""
    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)
    token_type = fields.String(default='bearer')

# User profile schema
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

# Login schemas
class LoginRequestSchema(Schema):
    """Schema for login request validation."""
    email = fields.Email(required=True)
    password = fields.String(required=True)
    rememberMe = fields.Boolean(required=False, default=False)

class LoginResponseSchema(Schema):
    """Schema for login response."""
    success = fields.Boolean(dump_only=True, default=True)
    message = fields.String(dump_only=True)
    tokens = fields.Nested(TokenResponseSchema, required=True)
    user = fields.Nested(UserProfileResponseSchema, required=True)

# Register schemas
class RegisterRequestSchema(Schema):
    """Schema for user registration validation."""
    email = fields.Email(required=True)
    password = fields.String(
        required=True,
        validate=validate.Length(min=8)
    )
    username = fields.String(
        required=True,
        validate=[
            validate.Length(min=3, max=50),
            validate.Regexp(
                "^[a-zA-Z0-9_-]+$",
                error="Username can only contain letters, numbers, underscores, and hyphens"
            )
        ]
    )
    firstName = fields.String(
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    lastName = fields.String(
        required=True,
        validate=validate.Length(min=1, max=50)
    )

    @post_load
    def create_full_name(self, data, **kwargs):
        """Combine firstName and lastName into full_name after validation."""
        data['full_name'] = f"{data['firstName']} {data['lastName']}"
        return data

class RegisterResponseSchema(Schema):
    """Schema for registration response."""
    message = fields.String()
    user = fields.Nested(lambda: UserProfileResponseSchema())
    success = fields.Boolean(default=True)
    tokens = fields.Nested(lambda: TokenResponseSchema())

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
