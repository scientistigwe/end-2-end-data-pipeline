# app/services/settings/settings_service.py
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from .....db.models.settings import (
    UserSettings,
    SystemSettings
)

from .....db.models.auth import User


class SettingsService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def get_user_settings(self, user_id: UUID) -> Dict[str, Any]:
        """Get user settings."""
        try:
            settings = self._get_or_create_user_settings(user_id)
            return {
                'preferences': settings.preferences,
                'appearance': settings.appearance,
                'notifications': settings.notifications,
                'privacy': settings.privacy
            }
        except Exception as e:
            self.logger.error(f"Error getting user settings: {str(e)}")
            raise

    def update_user_settings(self, user_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user settings."""
        try:
            settings = self._get_or_create_user_settings(user_id)
            
            # Update settings
            if 'preferences' in data:
                settings.preferences.update(data['preferences'])
            if 'appearance' in data:
                settings.appearance.update(data['appearance'])
            if 'notifications' in data:
                settings.notifications.update(data['notifications'])
            if 'privacy' in data:
                settings.privacy.update(data['privacy'])
                
            self.db_session.commit()
            
            return {
                'preferences': settings.preferences,
                'appearance': settings.appearance,
                'notifications': settings.notifications,
                'privacy': settings.privacy
            }
        except Exception as e:
            self.logger.error(f"Error updating user settings: {str(e)}")
            self.db_session.rollback()
            raise

    def get_notification_settings(self, user_id: UUID) -> Dict[str, Any]:
        """Get notification settings."""
        try:
            settings = self._get_or_create_user_settings(user_id)
            return settings.notifications
        except Exception as e:
            self.logger.error(f"Error getting notification settings: {str(e)}")
            raise

    def update_notification_settings(self, user_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update notification settings."""
        try:
            settings = self._get_or_create_user_settings(user_id)
            settings.notifications.update(data)
            self.db_session.commit()
            return settings.notifications
        except Exception as e:
            self.logger.error(f"Error updating notification settings: {str(e)}")
            self.db_session.rollback()
            raise

    def get_security_settings(self, user_id: UUID) -> Dict[str, Any]:
        """Get security settings."""
        try:
            user = self.db_session.query(User).get(user_id)
            if not user:
                raise ValueError("User not found")
                
            return {
                'two_factor_enabled': user.two_factor_enabled,
                'last_password_change': user.last_password_change,
                'security_questions': user.security_questions
            }
        except Exception as e:
            self.logger.error(f"Error getting security settings: {str(e)}")
            raise

    def update_security_settings(self, user_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update security settings."""
        try:
            user = self.db_session.query(User).get(user_id)
            if not user:
                raise ValueError("User not found")
                
            if 'two_factor_enabled' in data:
                user.two_factor_enabled = data['two_factor_enabled']
            if 'security_questions' in data:
                user.security_questions = data['security_questions']
                
            self.db_session.commit()
            
            return {
                'two_factor_enabled': user.two_factor_enabled,
                'last_password_change': user.last_password_change,
                'security_questions': user.security_questions
            }
        except Exception as e:
            self.logger.error(f"Error updating security settings: {str(e)}")
            self.db_session.rollback()
            raise

    def get_appearance_settings(self, user_id: UUID) -> Dict[str, Any]:
        """Get appearance settings."""
        try:
            settings = self._get_or_create_user_settings(user_id)
            return settings.appearance
        except Exception as e:
            self.logger.error(f"Error getting appearance settings: {str(e)}")
            raise

    def update_appearance_settings(self, user_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update appearance settings."""
        try:
            settings = self._get_or_create_user_settings(user_id)
            settings.appearance.update(data)
            self.db_session.commit()
            return settings.appearance
        except Exception as e:
            self.logger.error(f"Error updating appearance settings: {str(e)}")
            self.db_session.rollback()
            raise

    def get_system_settings(self) -> Dict[str, Any]:
        """Get system settings."""
        try:
            settings = {}
            system_settings = self.db_session.query(SystemSettings).all()
            
            for setting in system_settings:
                settings[setting.key] = setting.value
                
            return settings
        except Exception as e:
            self.logger.error(f"Error getting system settings: {str(e)}")
            raise

    def update_system_settings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update system settings."""
        try:
            for key, value in data.items():
                setting = self.db_session.query(SystemSettings).filter_by(key=key).first()
                if setting:
                    setting.value = value
                else:
                    setting = SystemSettings(key=key, value=value)
                    self.db_session.add(setting)
                    
            self.db_session.commit()
            return self.get_system_settings()
        except Exception as e:
            self.logger.error(f"Error updating system settings: {str(e)}")
            self.db_session.rollback()
            raise

    def validate_settings(self, data: Dict[str, Any]) -> Dict[str, bool]:
        """Validate settings configuration."""
        try:
            # Implement settings validation logic
            return {'valid': True}
        except Exception as e:
            self.logger.error(f"Error validating settings: {str(e)}")
            raise

    def reset_settings(self, user_id: UUID, settings_type: str = 'all') -> Dict[str, Any]:
        """Reset settings to defaults."""
        try:
            settings = self._get_or_create_user_settings(user_id)
            
            if settings_type == 'all' or settings_type == 'preferences':
                settings.preferences = {}
            if settings_type == 'all' or settings_type == 'appearance':
                settings.appearance = {}
            if settings_type == 'all' or settings_type == 'notifications':
                settings.notifications = {}
            if settings_type == 'all' or settings_type == 'privacy':
                settings.privacy = {}
                
            self.db_session.commit()
            
            return {
                'message': f'Successfully reset {settings_type} settings',
                'settings': self.get_user_settings(user_id)
            }
        except Exception as e:
            self.logger.error(f"Error resetting settings: {str(e)}")
            self.db_session.rollback()
            raise

    def _get_or_create_user_settings(self, user_id: UUID) -> UserSettings:
        """Get or create user settings."""
        settings = self.db_session.query(UserSettings).filter_by(user_id=user_id).first()
        if not settings:
            settings = UserSettings(
                user_id=user_id,
                preferences={},
                appearance={},
                notifications={},
                privacy={}
            )
            self.db_session.add(settings)
            self.db_session.commit()
        return settings