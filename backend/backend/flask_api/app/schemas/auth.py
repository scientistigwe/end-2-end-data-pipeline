from marshmallow import Schema, fields, validate, ValidationError, post_load
from datetime import datetime

# Custom validators
def password_validator(password):
    """Validate password strength."""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    if not any(char.isupper() for char in password):
        raise ValidationError("Password must contain at least one uppercase letter")
    if not any(char.islower() for char in password):
        raise ValidationError("Password must contain at least one lowercase letter")
    if not any(char.isdigit() for char in password):
        raise ValidationError("Password must contain at least one number")
    if not any(char in "!@#$%^&*()_+-=[]{}|;:,.<>?" for char in password):
        raise ValidationError("Password must contain at least one special character")

def name_validator(name):
    """Validate name format."""
    if not name or not name.strip():
        raise ValidationError("Name cannot be empty")
    if not all(char.isalpha() or char.isspace() for char in name):
        raise ValidationError("Name can only contain letters and spaces")
    if len(name.strip()) < 2:
        raise ValidationError("Name must be at least 2 characters long")

# Token schemas
class TokenResponseSchema(Schema):
    """Schema for token response serialization."""
    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)
    token_type = fields.String(default='bearer')
    expires_in = fields.Integer()
    issued_at = fields.DateTime(default=datetime.utcnow)

# User profile schema
class UserProfileResponseSchema(Schema):
    """Schema for user profile response."""
    id = fields.UUID(dump_only=True)
    email = fields.Email(dump_only=True)
    first_name = fields.String()
    last_name = fields.String()
    full_name = fields.String(dump_only=True)
    role = fields.String(dump_only=True)
    status = fields.String(dump_only=True)
    is_active = fields.Boolean(dump_only=True)
    last_login = fields.DateTime(dump_only=True)
    email_verified = fields.Boolean(dump_only=True)
    profile_image = fields.String()
    phone_number = fields.String()
    department = fields.String()
    timezone = fields.String()
    locale = fields.String()
    preferences = fields.Dict()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

# Login schemas
class LoginRequestSchema(Schema):
    """Schema for login request validation."""
    email = fields.Email(required=True)
    password = fields.String(required=True)
    rememberMe = fields.Boolean(load_default=False)
    device_info = fields.Dict(load_default=dict)

class LoginResponseSchema(Schema):
    """Schema for login response."""
    success = fields.Boolean(dump_only=True, default=True)
    message = fields.String(dump_only=True)
    user = fields.Nested(UserProfileResponseSchema, required=True)
    tokens = fields.Nested(TokenResponseSchema, required=True)
    logged_in_at = fields.DateTime(dump_only=True)
    last_login = fields.DateTime(dump_only=True)

# Register schemas
# Schema for basic registration
class RegisterRequestSchema(Schema):
    """Schema for user registration validation."""
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=password_validator)
    username = fields.String(required=True, validate=validate.Length(min=3, max=50))
    firstName = fields.String(required=True, validate=name_validator)  # Match frontend camelCase
    lastName = fields.String(required=True, validate=name_validator)   # Match frontend camelCase
    
    # Optional fields
    phoneNumber = fields.String(validate=validate.Length(max=50), load_default=None)
    department = fields.String(validate=validate.Length(max=100), load_default=None)
    timezone = fields.String(load_default='UTC')
    locale = fields.String(load_default='en')
    preferences = fields.Dict(load_default=dict)

    # class Meta:
        # unknown = EXCLUDE  # Ignore unknown fields

    @post_load
    def process_data(self, data, **kwargs):
        """Process and standardize data after validation."""
        data['email'] = data['email'].lower()
        # Convert camelCase to snake_case for database
        data['first_name'] = data.pop('firstName')
        data['last_name'] = data.pop('lastName')
        data['phone_number'] = data.pop('phoneNumber', None)
        return data

# Schema for profile updates
class UpdateProfileRequestSchema(Schema):
    """Schema for profile update validation."""
    firstName = fields.String(validate=name_validator)
    lastName = fields.String(validate=name_validator)
    phoneNumber = fields.String(validate=validate.Length(max=50))
    department = fields.String(validate=validate.Length(max=100))
    profileImage = fields.String()
    timezone = fields.String()
    locale = fields.String()
    preferences = fields.Dict()

    # class Meta:
        # unknown = EXCLUDE

    @post_load
    def process_data(self, data, **kwargs):
        """Convert camelCase to snake_case."""
        if 'firstName' in data:
            data['first_name'] = data.pop('firstName')
        if 'lastName' in data:
            data['last_name'] = data.pop('lastName')
        if 'phoneNumber' in data:
            data['phone_number'] = data.pop('phoneNumber')
        return data
    
class RegisterResponseSchema(Schema):
    """Schema for registration response."""
    message = fields.String()
    user = fields.Nested(UserProfileResponseSchema)
    success = fields.Boolean(default=True)
    tokens = fields.Nested(TokenResponseSchema)
    verification_email_sent = fields.Boolean(default=True)

# Password reset schemas
class PasswordResetRequestSchema(Schema):
    """Schema for password reset validation."""
    token = fields.String(required=True)
    new_password = fields.String(required=True, validate=password_validator)
    confirm_password = fields.String(required=True)

    @post_load
    def verify_passwords_match(self, data, **kwargs):
        """Verify that passwords match."""
        if data['new_password'] != data['confirm_password']:
            raise ValidationError("Passwords do not match")
        return data

class PasswordResetResponseSchema(Schema):
    """Schema for password reset response."""
    message = fields.String()
    success = fields.Boolean()
    reset_at = fields.DateTime()

# Email verification schemas
class EmailVerificationRequestSchema(Schema):
    """Schema for email verification validation."""
    token = fields.String(required=True)

class EmailVerificationResponseSchema(Schema):
    """Schema for email verification response."""
    message = fields.String()
    success = fields.Boolean()
    verified_at = fields.DateTime()

# Change password schemas
class ChangePasswordRequestSchema(Schema):
    """Schema for password change validation."""
    current_password = fields.String(required=True)
    new_password = fields.String(required=True, validate=password_validator)
    confirm_password = fields.String(required=True)

    @post_load
    def verify_passwords_match(self, data, **kwargs):
        """Verify that passwords match."""
        if data['new_password'] != data['confirm_password']:
            raise ValidationError("Passwords do not match")
        return data

class ChangePasswordResponseSchema(Schema):
    """Schema for password change response."""
    message = fields.String()
    success = fields.Boolean()
    changed_at = fields.DateTime()

# Profile update schema
class UpdateProfileRequestSchema(Schema):
    """Schema for profile update validation."""
    first_name = fields.String(validate=name_validator)
    last_name = fields.String(validate=name_validator)
    phone_number = fields.String(validate=validate.Length(max=50))
    department = fields.String(validate=validate.Length(max=100))
    timezone = fields.String()
    locale = fields.String()
    preferences = fields.Dict()

class UpdateProfileResponseSchema(Schema):
    """Schema for profile update response."""
    message = fields.String()
    success = fields.Boolean()
    user = fields.Nested(UserProfileResponseSchema)
    updated_at = fields.DateTime()