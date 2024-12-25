# app/blueprints/settings/routes.py
from flask import Blueprint, request, g
from marshmallow import ValidationError
from ...schemas.settings import (
   # User settings schemas
   UserSettingsRequestSchema,
   UserSettingsResponseSchema,
   UserPreferencesUpdateSchema,
   
   # Notification settings schemas
   NotificationSettingsSchema,
   
   # Security settings schemas
   SecuritySettingsRequestSchema,
   SecuritySettingsResponseSchema,
   
   # Appearance settings schemas
   AppearanceSettingsSchema,
   
   # System settings schemas
   SystemSettingsRequestSchema,
   SystemSettingsResponseSchema,
   
   # Validation schemas
   ValidationRequestSchema,
   ValidationResponseSchema
)
from ...services.settings import SettingsService
from ...utils.response_builder import ResponseBuilder
import logging

logger = logging.getLogger(__name__)
settings_bp = Blueprint('settings', __name__)

def get_settings_service():
    """Get settings service instance."""
    if 'settings_service' not in g:
        g.settings_service = SettingsService(g.db)
    return g.settings_service

@settings_bp.route('/profile', methods=['GET', 'PUT'])
def manage_profile_settings():
    """Get or update profile settings."""
    try:
        settings_service = get_settings_service()
        user_id = g.current_user.id

        if request.method == 'GET':
            settings = settings_service.get_user_settings(user_id)
            return ResponseBuilder.success(
                UserSettingsResponseSchema().dump({'settings': settings})
            )

        schema = UserSettingsRequestSchema()
        data = schema.load(request.get_json())
        settings = settings_service.update_user_settings(user_id, data)
        return ResponseBuilder.success(
            UserSettingsResponseSchema().dump({'settings': settings})
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"Error managing profile settings: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to manage profile settings", status_code=500)

@settings_bp.route('/notifications', methods=['GET', 'PUT'])
def manage_notification_settings():
    """Get or update notification settings."""
    try:
        settings_service = get_settings_service()
        user_id = g.current_user.id

        if request.method == 'GET':
            settings = settings_service.get_notification_settings(user_id)
            return ResponseBuilder.success({'settings': settings})

        schema = NotificationSettingsSchema()
        data = schema.load(request.get_json())
        settings = settings_service.update_notification_settings(user_id, data)
        return ResponseBuilder.success({'settings': settings})
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"Error managing notification settings: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to manage notification settings", status_code=500)

@settings_bp.route('/security', methods=['GET', 'PUT'])
def manage_security_settings():
    """Get or update security settings."""
    try:
        settings_service = get_settings_service()
        user_id = g.current_user.id

        if request.method == 'GET':
            settings = settings_service.get_security_settings(user_id)
            return ResponseBuilder.success(
                SecuritySettingsResponseSchema().dump({'settings': settings})
            )

        schema = SecuritySettingsRequestSchema()
        data = schema.load(request.get_json())
        settings = settings_service.update_security_settings(user_id, data)
        return ResponseBuilder.success(
            SecuritySettingsResponseSchema().dump({'settings': settings})
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"Error managing security settings: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to manage security settings", status_code=500)

@settings_bp.route('/appearance', methods=['GET', 'PUT'])
def manage_appearance_settings():
    """Get or update appearance settings."""
    try:
        settings_service = get_settings_service()
        user_id = g.current_user.id

        if request.method == 'GET':
            settings = settings_service.get_appearance_settings(user_id)
            return ResponseBuilder.success({'settings': settings})

        schema = AppearanceSettingsSchema()
        data = schema.load(request.get_json())
        settings = settings_service.update_appearance_settings(user_id, data)
        return ResponseBuilder.success({'settings': settings})
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"Error managing appearance settings: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to manage appearance settings", status_code=500)

@settings_bp.route('/system', methods=['GET', 'PUT'])
def manage_system_settings():
    """Get or update system settings."""
    try:
        settings_service = get_settings_service()
        user_id = g.current_user.id

        if request.method == 'GET':
            settings = settings_service.get_system_settings()
            return ResponseBuilder.success(
                SystemSettingsResponseSchema().dump({'settings': settings})
            )

        schema = SystemSettingsRequestSchema()
        data = schema.load(request.get_json())
        settings = settings_service.update_system_settings(data)
        return ResponseBuilder.success(
            SystemSettingsResponseSchema().dump({'settings': settings})
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"Error managing system settings: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to manage system settings", status_code=500)

@settings_bp.route('/validate', methods=['POST'])
def validate_settings():
    """Validate settings configuration."""
    try:
        settings_service = get_settings_service()
        schema = ValidationRequestSchema()
        data = schema.load(request.get_json())
        result = settings_service.validate_settings(data)
        return ResponseBuilder.success(
            ValidationResponseSchema().dump({'result': result})
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"Error validating settings: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to validate settings", status_code=500)

@settings_bp.route('/reset', methods=['POST'])
def reset_settings():
    """Reset settings to defaults."""
    try:
        settings_service = get_settings_service()
        user_id = g.current_user.id
        settings_type = request.json.get('type', 'all')
        result = settings_service.reset_settings(user_id, settings_type)
        return ResponseBuilder.success({'result': result})
    except Exception as e:
        logger.error(f"Error resetting settings: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to reset settings", status_code=500)

# Error handlers
@settings_bp.errorhandler(404)
def not_found_error(error):
    return ResponseBuilder.error("Resource not found", status_code=404)

@settings_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}", exc_info=True)
    return ResponseBuilder.error("Internal server error", status_code=500)