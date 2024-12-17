# models/auth.py
from sqlalchemy import Column, String, DateTime, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel
import uuid

class User(BaseModel):
    __tablename__ = 'users'

    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    status = Column(Enum('active', 'inactive', 'suspended', name='user_status'), default='active')
    role = Column(String(50), default='user')
    last_login = Column(DateTime)
    email_verified = Column(Boolean, default=False)
    profile_image = Column(String(255))
    preferences = Column(JSON)

class UserSession(BaseModel):
    __tablename__ = 'user_sessions'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(String(255))