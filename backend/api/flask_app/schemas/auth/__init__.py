# schemas/auth/__init__.py
from .base import password_validator, name_validator
from .tokens import TokenRequestSchema, TokenResponseSchema
from .user import UserProfileSchema, UpdateProfileRequestSchema, UpdateProfileResponseSchema
from .login import LoginRequestSchema, LoginResponseSchema
from .registration import RegistrationRequestSchema, RegistrationResponseSchema
from .verification import EmailVerificationRequestSchema, EmailVerificationResponseSchema
from .password import (
    PasswordResetRequestSchema, PasswordResetResponseSchema,
    ChangePasswordRequestSchema, ChangePasswordResponseSchema
)
from .session import SessionRequestSchema, SessionResponseSchema
from .mfa import (
    MFASetupRequestSchema, MFASetupResponseSchema,
    MFAVerifyRequestSchema, MFAVerifyResponseSchema
)
from .roles import RoleRequestSchema, RoleResponseSchema
from .permissions import PermissionRequestSchema, PermissionResponseSchema
from .audit import AuditLogSchema

__all__ = [
    # Base
    'password_validator', 'name_validator',

    # Tokens
    'TokenRequestSchema', 'TokenResponseSchema',

    # User
    'UserProfileSchema', 'UpdateProfileRequestSchema', 'UpdateProfileResponseSchema',

    # Login
    'LoginRequestSchema', 'LoginResponseSchema',

    # Registration
    'RegistrationRequestSchema', 'RegistrationResponseSchema',

    # Verification
    'EmailVerificationRequestSchema', 'EmailVerificationResponseSchema',

    # Password
    'PasswordResetRequestSchema', 'PasswordResetResponseSchema',
    'ChangePasswordRequestSchema', 'ChangePasswordResponseSchema',

    # Session
    'SessionRequestSchema', 'SessionResponseSchema',

    # MFA
    'MFASetupRequestSchema', 'MFASetupResponseSchema',
    'MFAVerifyRequestSchema', 'MFAVerifyResponseSchema',

    # Roles
    'RoleRequestSchema', 'RoleResponseSchema',

    # Permissions
    'PermissionRequestSchema', 'PermissionResponseSchema',

    # Audit
    'AuditLogSchema'
]