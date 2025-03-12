# backend/api/fastapi_app/schemas/auth.py

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import (
    BaseModel, EmailStr, Field, model_validator,
    constr, ConfigDict
)
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    MANAGER = "manager"
    GUEST = "guest"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class MFAType(str, Enum):
    APP = "app"
    SMS = "sms"
    EMAIL = "email"


class StagingRequestSchema(BaseModel):
    """Base request schema maintained for compatibility"""
    model_config = ConfigDict(from_attributes=True)


class StagingResponseSchema(BaseModel):
    """Base response schema maintained for compatibility"""
    model_config = ConfigDict(from_attributes=True)


# User Profile Schemas - Move these to the top since they're referenced by other schemas
class UserProfileResponse(BaseModel):
    id: Optional[str]
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    full_name: str
    role: str
    status: str
    email_verified: bool = False
    timezone: Optional[str]
    locale: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class UserProfileSchema(BaseModel):
    id: str
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    full_name: str
    role: str
    permissions: List[str] = Field(default_factory=list)
    status: UserStatus
    email_verified: bool
    profile_image: Optional[str]
    phone_number: Optional[str]
    department: Optional[str]
    timezone: Optional[str]
    locale: Optional[str]
    preferences: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    security_level: int = Field(ge=0, le=10)

    model_config = ConfigDict(from_attributes=True)


# Token Schemas
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str

    model_config = ConfigDict(from_attributes=True)


# Login Schemas
class LoginResponseSchema(BaseModel):
    user: UserProfileResponse
    tokens: TokenResponse
    mfa_required: bool = False
    session_expires: datetime
    permitted_actions: List[str] = Field(default_factory=list)


class LoginRequestSchema(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False
    device_info: Dict[str, Any] = Field(default_factory=dict)
    mfa_code: Optional[str]


# Password Reset Schema
class PasswordResetRequestSchema(StagingRequestSchema):
    token: str
    email: EmailStr
    new_password: str
    confirm_password: str

    @model_validator(mode='after')
    def validate_passwords(self) -> 'PasswordResetRequestSchema':
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords must match')
        return self


class PasswordResetResponseSchema(StagingResponseSchema):
    reset_at: datetime
    requires_reverification: bool


class ChangePasswordRequestSchema(StagingRequestSchema):
    current_password: str
    new_password: str
    confirm_password: str

    @model_validator(mode='after')
    def validate_passwords(self) -> 'ChangePasswordRequestSchema':
        if self.new_password == self.current_password:
            raise ValueError('New password must be different')
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords must match')
        return self


class ChangePasswordResponseSchema(StagingResponseSchema):
    changed_at: datetime
    requires_relogin: bool


# MFA Schemas
class MFASetupRequestSchema(StagingRequestSchema):
    mfa_type: MFAType
    phone_number: Optional[str]
    backup_codes: List[str] = Field(default_factory=list)


class MFASetupResponseSchema(StagingResponseSchema):
    secret_key: str
    qr_code: str
    backup_codes: List[str]


class MFAVerifyRequestSchema(StagingRequestSchema):
    code: str
    mfa_type: MFAType
    remember_device: bool = False


class MFAVerifyResponseSchema(StagingResponseSchema):
    verified: bool
    token: TokenResponse
    device_token: str


# Registration Schema
class RegistrationRequestSchema(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str
    username: constr(min_length=3, max_length=50)
    first_name: str
    last_name: str
    terms_accepted: bool = Field(..., description="Must accept terms and conditions")
    timezone: str = 'UTC'
    locale: str = 'en'

    @model_validator(mode='after')
    def validate_passwords(self) -> 'RegistrationRequestSchema':
        if self.password != self.confirm_password:
            raise ValueError('Passwords must match')
        return self

    model_config = ConfigDict(from_attributes=True)


class RegistrationResponseSchema(BaseModel):
    user: UserProfileResponse
    verification_email_sent: bool

    model_config = ConfigDict(from_attributes=True)


# Permission Schemas
class PermissionRequestSchema(StagingRequestSchema):
    name: str
    description: Optional[str]
    resource_type: str
    actions: List[str]
    conditions: Dict[str, Any] = Field(default_factory=dict)


class PermissionResponseSchema(StagingResponseSchema):
    name: str
    description: Optional[str]
    resource_type: str
    actions: List[str]
    conditions: Dict[str, Any] = Field(default_factory=dict)
    roles: List[str]


class RoleResponseSchema(StagingResponseSchema):
    name: str
    description: Optional[str]
    permissions: List[str]
    scope: str
    assigned_users: int



class SessionResponseSchema(StagingResponseSchema):
    session_id: UUID
    expires_at: datetime
    last_accessed: datetime
    active_sessions: int


# Role Schemas
class RoleRequestSchema(StagingRequestSchema):
    name: str
    description: Optional[str]
    permissions: List[str]
    scope: str = Field(..., pattern='^(global|tenant|user)$')


class SessionRequestSchema(StagingRequestSchema):
    session_id: UUID
    action: str = Field(..., pattern='^(extend|terminate|refresh)$')
    device_info: Dict[str, Any] = Field(default_factory=dict)


# Token Schema Updates
class TokenRequestSchema(BaseModel):
    token_type: str = Field(..., pattern='^(access|refresh)$')
    client_id: str
    client_secret: str
    scope: Optional[List[str]]

    model_config = ConfigDict(from_attributes=True)

class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    scope: List[str] = Field(default_factory=list)
    issued_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


# Email Verification Schemas
class EmailVerificationRequestSchema(StagingRequestSchema):
    token: str
    email: EmailStr


class EmailVerificationResponseSchema(StagingResponseSchema):
    verified_at: datetime
    user: UserProfileResponse


# Profile Update Schemas
class UpdateProfileRequestSchema(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    phone_number: Optional[str]
    department: Optional[str]
    preferences: Optional[Dict[str, Any]]


class UpdateProfileResponseSchema(BaseModel):
    profile: UserProfileSchema
    updated_at: datetime

class StagingRequestSchema(BaseModel):
    """Base request schema maintained for compatibility"""
    model_config = ConfigDict(from_attributes=True)


class StagingResponseSchema(BaseModel):
    """Base response schema maintained for compatibility"""
    model_config = ConfigDict(from_attributes=True)


# Audit Schemas
class AuditLogSchema(StagingResponseSchema):
    action: str
    actor_id: UUID
    actor_type: str
    target_id: UUID
    target_type: str
    changes: Dict[str, Any] = Field(default_factory=dict)
    ip_address: str
    user_agent: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


