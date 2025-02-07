# backend/api/fastapi_app/schemas/auth.py

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, validator, root_validator, constr
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
    class Config:
        orm_mode = True


class StagingResponseSchema(BaseModel):
    """Base response schema maintained for compatibility"""
    class Config:
        orm_mode = True


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


# Login Schemas
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

    class Config:
        orm_mode = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str

    class Config:
        orm_mode = True


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


# Password Schemas
class PasswordResetRequestSchema(StagingRequestSchema):
    token: str
    email: EmailStr
    new_password: str
    confirm_password: str

    @root_validator
    def validate_passwords(cls, values):
        if values.get('new_password') != values.get('confirm_password'):
            raise ValueError('Passwords must match')
        return values


class PasswordResetResponseSchema(StagingResponseSchema):
    reset_at: datetime
    requires_reverification: bool


class ChangePasswordRequestSchema(StagingRequestSchema):
    current_password: str
    new_password: str
    confirm_password: str

    @root_validator
    def validate_passwords(cls, values):
        if values.get('new_password') == values.get('current_password'):
            raise ValueError('New password must be different')
        if values.get('new_password') != values.get('confirm_password'):
            raise ValueError('Passwords must match')
        return values


class ChangePasswordResponseSchema(StagingResponseSchema):
    changed_at: datetime
    requires_relogin: bool


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


# Registration Schemas
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

    @root_validator
    def validate_passwords(cls, values):
        if values.get('password') != values.get('confirm_password'):
            raise ValueError('Passwords must match')
        return values


class RegistrationResponseSchema(BaseModel):
    user: UserProfileResponse
    verification_email_sent: bool


# Role Schemas
class RoleRequestSchema(StagingRequestSchema):
    name: str
    description: Optional[str]
    permissions: List[str]
    scope: str = Field(..., regex='^(global|tenant|user)$')


class RoleResponseSchema(StagingResponseSchema):
    name: str
    description: Optional[str]
    permissions: List[str]
    scope: str
    assigned_users: int


# Session Schemas
class SessionRequestSchema(StagingRequestSchema):
    session_id: UUID
    action: str = Field(..., regex='^(extend|terminate|refresh)$')
    device_info: Dict[str, Any] = Field(default_factory=dict)


class SessionResponseSchema(StagingResponseSchema):
    session_id: UUID
    expires_at: datetime
    last_accessed: datetime
    active_sessions: int


# Token Schemas
class TokenRequestSchema(BaseModel):
    token_type: str = Field(..., regex='^(access|refresh)$')
    client_id: str
    client_secret: str
    scope: Optional[List[str]]

    class Config:
        orm_mode = True


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    scope: List[str] = Field(default_factory=list)
    issued_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True


# Email Verification Schemas
class EmailVerificationRequestSchema(StagingRequestSchema):
    token: str
    email: EmailStr


class EmailVerificationResponseSchema(StagingResponseSchema):
    verified_at: datetime
    user: UserProfileResponse


# User Profile Schemas
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

    class Config:
        orm_mode = True


class UpdateProfileRequestSchema(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    phone_number: Optional[str]
    department: Optional[str]
    preferences: Optional[Dict[str, Any]]


class UpdateProfileResponseSchema(BaseModel):
    profile: UserProfileSchema
    updated_at: datetime