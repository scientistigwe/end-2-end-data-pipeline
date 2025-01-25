# backend/db/models/staging/settings_output_model.py
from typing import Dict, Any
from sqlalchemy.orm import relationship
from sqlalchemy.orm import column_property
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from datetime import datetime
from core.messaging.event_types import ComponentType
from .base_staging_model import BaseStagedOutput


class StagedSettingsOutput(BaseStagedOutput):
    """Model for storing settings data in the staging system."""
    __tablename__ = 'staging_settings_output'

    base_id = Column(UUID(as_uuid=True), ForeignKey('staged_outputs.id'), primary_key=True)

    # Settings categories
    preferences = Column(JSON, default=dict)
    appearance = Column(JSON, default=dict)
    notifications = Column(JSON, default=dict)
    privacy = Column(JSON, default=dict)
    security = Column(JSON, default=dict)

    # System settings if applicable
    system_settings = Column(JSON, default=dict)

    # Versioning and change tracking
    settings_version = Column(String(36))
    previous_version = Column(String(36))
    change_history = Column(JSON, default=list)

    # Metadata and timestamps with unique column names
    staged_settings_metadata = Column(JSON, default=dict)
    settings_created_at = column_property(Column(DateTime, default=datetime.utcnow))
    settings_updated_at = column_property(Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    base_output = relationship("BaseStagedOutput", back_populates="settings_output")

    __mapper_args__ = {
        "polymorphic_identity": "staging.settings_output",
        "inherit_condition": base_id == BaseStagedOutput.id
    }

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            'id': self.id,
            'reference_id': self.reference_id,
            'pipeline_id': self.pipeline_id,
            'user_id': self.user_id,
            'settings': {
                'preferences': self.preferences,
                'appearance': self.appearance,
                'notifications': self.notifications,
                'privacy': self.privacy,
                'security': self.security
            },
            'system_settings': self.system_settings,
            'version_info': {
                'settings_version': self.settings_version,
                'previous_version': self.previous_version,
                'change_history': self.change_history
            },
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SettingsOutput':
        """Create model instance from dictionary."""
        instance = cls()

        # Map basic fields
        instance.id = data.get('id')
        instance.reference_id = data.get('reference_id')
        instance.pipeline_id = data.get('pipeline_id')
        instance.user_id = data.get('user_id')

        # Map settings categories
        settings = data.get('settings', {})
        instance.preferences = settings.get('preferences', {})
        instance.appearance = settings.get('appearance', {})
        instance.notifications = settings.get('notifications', {})
        instance.privacy = settings.get('privacy', {})
        instance.security = settings.get('security', {})

        # Map system settings
        instance.system_settings = data.get('system_settings', {})

        # Map version info
        version_info = data.get('version_info', {})
        instance.settings_version = version_info.get('settings_version')
        instance.previous_version = version_info.get('previous_version')
        instance.change_history = version_info.get('change_history', [])

        # Map metadata
        instance.metadata = data.get('metadata', {})

        return instance