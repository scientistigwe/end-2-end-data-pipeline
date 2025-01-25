# flask_app/blueprints/settings/routes.py

from flask import Blueprint, request, g, current_app
from marshmallow import ValidationError
from datetime import datetime
import logging
from typing import Dict, Any

from ...schemas.staging.settings import (
    SettingsStagingRequestSchema,
    SettingsStagingResponseSchema
)
from ...utils.error_handlers import (
    handle_validation_error,
    handle_service_error,
    handle_not_found_error
)
from ...utils.response_builder import ResponseBuilder

from core.messaging.event_types import (
    ComponentType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage
)

logger = logging.getLogger(__name__)


def create_settings_blueprint(settings_service, staging_manager):
    """
    Create settings blueprint with comprehensive staging integration.

    Args:
        settings_service: Service for settings operations
        staging_manager: Manager for staging operations

    Returns:
        Blueprint: Configured settings routes
    """
    settings_bp = Blueprint('settings', __name__)

    @settings_bp.route('/<category>/update', methods=['POST'])
    async def update_settings(category):
        """Update settings with staging integration."""
        try:
            schema = SettingsStagingRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = g.current_user.id
            data['category'] = category

            # Stage settings update
            staging_ref = await staging_manager.stage_data(
                data=data,
                component_type=ComponentType.SETTINGS_SERVICE,
                pipeline_id=data.get('pipeline_id'),
                metadata={
                    'category': category,
                    'scope': data.get('scope', 'user'),
                    'update_time': datetime.utcnow().isoformat(),
                    'user_id': g.current_user.id
                }
            )

            # Apply settings update
            update_result = await settings_service.update_settings(
                data,
                staging_ref
            )

            return ResponseBuilder.success({
                'status': 'updated',
                'category': category,
                'staging_reference': staging_ref,
                'effective_time': datetime.utcnow().isoformat()
            })

        except ValidationError as ve:
            return handle_validation_error(ve)
        except Exception as e:
            return handle_service_error(
                e,
                f"Failed to update {category} settings",
                logger
            )

    @settings_bp.route('/<category>', methods=['GET'])
    async def get_settings(category):
        """Get current settings with effective values."""
        try:
            settings = await settings_service.get_settings(
                category,
                user_id=g.current_user.id
            )

            # Get effective settings from staging
            if settings.staging_reference:
                effective_settings = await staging_manager.get_effective_settings(
                    settings.staging_reference
                )
                settings.effective_settings = effective_settings

            return ResponseBuilder.success(
                SettingsStagingResponseSchema().dump(settings)
            )

        except Exception as e:
            return handle_service_error(
                e,
                f"Failed to get {category} settings",
                logger
            )

    @settings_bp.route('/<category>/validate', methods=['POST'])
    async def validate_settings(category):
        """Validate settings configuration before applying."""
        try:
            validation_data = request.get_json()

            # Stage validation request
            staging_ref = await staging_manager.stage_data(
                data=validation_data,
                component_type=ComponentType.SETTINGS_SERVICE,
                metadata={
                    'operation': 'settings_validation',
                    'category': category,
                    'validation_time': datetime.utcnow().isoformat()
                }
            )

            # Validate settings
            validation_result = await settings_service.validate_settings(
                validation_data,
                category,
                staging_ref
            )

            return ResponseBuilder.success({
                'is_valid': validation_result.is_valid,
                'issues': validation_result.issues,
                'recommendations': validation_result.recommendations,
                'staging_reference': staging_ref
            })

        except Exception as e:
            return handle_service_error(
                e,
                f"Failed to validate {category} settings",
                logger
            )

    @settings_bp.route('/<category>/history', methods=['GET'])
    async def get_settings_history(category):
        """Get settings change history with detailed tracking."""
        try:
            history = await settings_service.get_settings_history(
                category,
                user_id=g.current_user.id
            )

            # Enrich with staging data
            if history.staging_references:
                for entry in history.changes:
                    staging_data = await staging_manager.get_change_details(
                        entry['staging_reference']
                    )
                    entry['change_details'] = staging_data

            return ResponseBuilder.success({
                'history': history.changes,
                'summary': history.summary
            })

        except Exception as e:
            return handle_service_error(
                e,
                f"Failed to get {category} settings history",
                logger
            )

    @settings_bp.route('/<category>/reset', methods=['POST'])
    async def reset_settings(category):
        """Reset settings to defaults with tracking."""
        try:
            reset_data = {
                'user_id': g.current_user.id,
                'reset_time': datetime.utcnow().isoformat(),
                'reason': request.get_json().get('reason')
            }

            # Stage reset operation
            staging_ref = await staging_manager.stage_data(
                data=reset_data,
                component_type=ComponentType.SETTINGS_SERVICE,
                metadata={
                    'operation': 'settings_reset',
                    'category': category
                }
            )

            # Perform reset
            reset_result = await settings_service.reset_settings(
                category,
                reset_data,
                staging_ref
            )

            return ResponseBuilder.success({
                'status': 'reset',
                'category': category,
                'staging_reference': staging_ref,
                'reset_time': reset_data['reset_time']
            })

        except Exception as e:
            return handle_service_error(
                e,
                f"Failed to reset {category} settings",
                logger
            )

    @settings_bp.route('/sync', methods=['POST'])
    async def sync_settings():
        """Synchronize settings across components."""
        try:
            sync_data = {
                'user_id': g.current_user.id,
                'sync_time': datetime.utcnow().isoformat(),
                'components': request.get_json().get('components', [])
            }

            # Stage sync operation
            staging_ref = await staging_manager.stage_data(
                data=sync_data,
                component_type=ComponentType.SETTINGS_SERVICE,
                metadata={
                    'operation': 'settings_sync',
                    'sync_scope': sync_data['components']
                }
            )

            # Perform synchronization
            sync_result = await settings_service.sync_settings(
                sync_data,
                staging_ref
            )

            return ResponseBuilder.success({
                'status': 'synchronized',
                'components': sync_data['components'],
                'staging_reference': staging_ref,
                'sync_time': sync_data['sync_time']
            })

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to synchronize settings",
                logger
            )

    @settings_bp.errorhandler(404)
    def not_found_error(error):
        """Handle resource not found errors."""
        return ResponseBuilder.error(
            "Resource not found",
            status_code=404
        )

    @settings_bp.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return ResponseBuilder.error(
            "Internal server error",
            status_code=500
        )

    return settings_bp