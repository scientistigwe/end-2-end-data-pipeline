# backend\backend\db\types\settings.py
from sqlalchemy import (
    Column, String, DateTime, Enum, ForeignKey, Boolean, Text,
    Index, UniqueConstraint, CheckConstraint, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel

class UserSettings(BaseModel):
    __tablename__ = 'user_settings'

    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='CASCADE'), 
        unique=True,
        nullable=False
    )
    preferences = Column(JSONB, default={})  
    appearance = Column(JSONB, default={})   
    notifications = Column(JSONB, default={}) 
    privacy = Column(JSONB, default={})      
    shortcuts = Column(JSONB, default={})    
    analytics = Column(JSONB, default={})    
    dashboard_config = Column(JSONB)
    email_preferences = Column(JSONB)
    data_display_settings = Column(JSONB)
    
    # Fix: Specify foreign key explicitly
    user = relationship(
        'User',
        foreign_keys=[user_id],
        back_populates='settings',
        uselist=False  # One-to-one relationship
    )

    def __repr__(self):
        return f"<UserSettings(user_id='{self.user_id}')>"


class SystemSettings(BaseModel):
    __tablename__ = 'system_settings'

    key = Column(String(255), unique=True, nullable=False)
    value = Column(JSONB)
    description = Column(Text)
    is_encrypted = Column(Boolean, default=False)
    category = Column(String(100))
    last_modified_by = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'),
        index=True
    )
    environment = Column(String(50))
    is_override = Column(Boolean, default=False)
    override_reason = Column(Text)
    
    # Add relationship
    modifier = relationship(
        'User',
        foreign_keys=[last_modified_by]
    )
    
    __table_args__ = (
        Index('ix_system_settings_category', 'category'),
        {'extend_existing': True}
    )

    def __repr__(self):
        return f"<SystemSettings(key='{self.key}')>"
    
    
class Integration(BaseModel):
    __tablename__ = 'integrations'

    name = Column(String(255), nullable=False)
    type = Column(String(100))
    config = Column(JSONB)
    status = Column(Enum('active', 'inactive', 'error', name='integration_status'))
    credentials = Column(JSONB)
    integration_meta = Column(JSONB)
    webhook_url = Column(String(255))
    api_key = Column(String(255))
    refresh_token = Column(String(255))
    expires_at = Column(DateTime)
    last_sync = Column(DateTime)
    sync_frequency = Column(Integer)  # minutes
    retry_config = Column(JSONB)
    error_handling = Column(JSONB)

    __table_args__ = (
        Index('ix_integrations_type_status', 'type', 'status'),
        CheckConstraint('sync_frequency > 0', name='ck_sync_frequency_positive'),
        {'extend_existing': True}
    )