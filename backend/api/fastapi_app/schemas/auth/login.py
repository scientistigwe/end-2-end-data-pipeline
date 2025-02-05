# schemas/auth/login.py
from marshmallow import Schema, fields, EXCLUDE

class UserProfileResponse(Schema):
    """Schema for user profile in responses"""
    id = fields.String()
    email = fields.String()
    username = fields.String()
    first_name = fields.String()
    last_name = fields.String()
    full_name = fields.String()
    role = fields.String()
    status = fields.String()
    email_verified = fields.Boolean()
    # Remove metadata and other complex fields temporarily
    timezone = fields.String(allow_none=True)
    locale = fields.String(allow_none=True)

    class Meta:
        unknown = EXCLUDE

class TokenResponse(Schema):
    """Schema for token data"""
    access_token = fields.String()
    refresh_token = fields.String()

    class Meta:
        unknown = EXCLUDE

class LoginResponseSchema(Schema):
    """Schema for login responses"""
    user = fields.Nested(UserProfileResponse)
    tokens = fields.Nested(TokenResponse)
    mfa_required = fields.Boolean(default=False)
    session_expires = fields.DateTime()
    permitted_actions = fields.List(fields.String(), default=[])

    class Meta:
        unknown = EXCLUDE

class LoginRequestSchema(Schema):
    """Schema for login requests"""
    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)
    rememberMe = fields.Boolean(load_default=False)
    device_info = fields.Dict(load_default=dict)
    mfa_code = fields.String(required=False)

    class Meta:
        unknown = EXCLUDE