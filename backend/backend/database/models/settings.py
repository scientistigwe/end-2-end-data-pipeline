# models/settings.py
from sqlalchemy import Column, String, DateTime, JSON, Enum, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel

class UserSettings(BaseModel):
    __tablename__ = 'user_settings'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), unique=True)
    preferences = Column(JSONB, default={})  # User preferences
    appearance = Column(JSONB, default={})   # UI settings
    notifications = Column(JSONB, default={}) # Notification preferences
    privacy = Column(JSONB, default={})      # Privacy settings
    shortcuts = Column(JSONB, default={})    # Keyboard shortcuts
    analytics = Column(JSONB, default={})    # Analytics preferences
    
    user = relationship('User', back_populates='settings')

class SystemSettings(BaseModel):
    __tablename__ = 'system_settings'

    key = Column(String(255), unique=True, nullable=False)
    value = Column(JSONB)
    description = Column(Text)
    is_encrypted = Column(Boolean, default=False)
    last_modified_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))

class Integration(BaseModel):
    __tablename__ = 'integrations'

    name = Column(String(255), nullable=False)
    type = Column(String(100))
    config = Column(JSONB)
    status = Column(Enum('active', 'inactive', 'error', name='integration_status'))
    credentials = Column(JSONB)
    integration_meta = Column(JSONB)