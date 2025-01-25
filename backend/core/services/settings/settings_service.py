# backend/core/services/settings/settings_service.py

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ComponentType,
    ModuleIdentifier,
    MessageMetadata
)
from core.staging.staging_manager import StagingManager

logger = logging.getLogger(__name__)


class SettingsService:
    """
    Service layer for settings management.
    Uses staging system for settings data persistence and versioning.
    """

    def __init__(
            self,
            staging_manager: StagingManager,
            message_broker: MessageBroker,
            initialize_async: bool = False
    ):
        self.staging_manager = staging_manager
        self.message_broker = message_broker

        self.module_identifier = ModuleIdentifier(
            component_name="settings_service",
            component_type=ComponentType.SETTINGS_SERVICE,
            department="settings",
            role="service"
        )

        self.logger = logger

        if initialize_async:
            asyncio.run(self._initialize_async())

    async def _initialize_async(self):
        await self._initialize_message_handlers()

    async def _initialize_message_handlers(self) -> None:
        handlers = {
            MessageType.SETTINGS_REQUEST: self._handle_settings_request,
            MessageType.SETTINGS_UPDATE: self._handle_settings_update,
            MessageType.SETTINGS_RESET: self._handle_settings_reset,
            MessageType.SYSTEM_SETTINGS_REQUEST: self._handle_system_settings_request,
            MessageType.SETTINGS_ERROR: self._handle_error
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=f"settings.{message_type.value}.#",
                callback=handler
            )

    async def _handle_settings_request(self, message: ProcessingMessage) -> None:
        """Handle settings request"""
        try:
            user_id = message.content.get('user_id')
            settings_type = message.content.get('settings_type', 'all')

            # Retrieve latest settings from staging
            staged_settings = await self._get_latest_settings(user_id)

            # Filter settings based on type if needed
            settings_data = self._filter_settings(staged_settings, settings_type)

            # Create new staging reference for this request
            reference_id = await self.staging_manager.stage_data(
                data=settings_data,
                component_type=ComponentType.SETTINGS_SERVICE,
                pipeline_id=message.content.get('pipeline_id'),
                metadata={
                    'user_id': user_id,
                    'settings_type': settings_type,
                    'request_timestamp': datetime.utcnow().isoformat()
                }
            )

            # Send response
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.SETTINGS_RESPONSE,
                    content={
                        'user_id': user_id,
                        'reference_id': reference_id,
                        'settings': settings_data,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component=message.metadata.source_component,
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle settings request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_settings_update(self, message: ProcessingMessage) -> None:
        """Handle settings update request"""
        try:
            user_id = message.content.get('user_id')
            update_data = message.content.get('settings', {})

            # Get current settings
            current_settings = await self._get_latest_settings(user_id)

            # Apply updates
            updated_settings = self._merge_settings(current_settings, update_data)

            # Store updated settings in staging
            reference_id = await self.staging_manager.stage_data(
                data=updated_settings,
                component_type=ComponentType.SETTINGS_SERVICE,
                pipeline_id=message.content.get('pipeline_id'),
                metadata={
                    'user_id': user_id,
                    'update_type': 'settings_update',
                    'previous_version': current_settings.get('version_info', {}).get('settings_version'),
                    'update_timestamp': datetime.utcnow().isoformat()
                }
            )

            # Send response
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.SETTINGS_UPDATE_COMPLETE,
                    content={
                        'user_id': user_id,
                        'reference_id': reference_id,
                        'settings': updated_settings,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component=message.metadata.source_component,
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle settings update: {str(e)}")
            await self._notify_error(message, str(e))

    async def _get_latest_settings(self, user_id: str) -> Dict[str, Any]:
        """Retrieve latest settings from staging"""
        # Get latest settings output for user
        outputs = await self.staging_manager.get_component_outputs(
            ComponentType.SETTINGS_SERVICE,
            metadata_filter={'user_id': user_id}
        )

        if not outputs:
            return self._get_default_settings()

        latest_output = max(outputs, key=lambda x: x.created_at)
        return latest_output.to_dict()

    def _filter_settings(self, settings: Dict[str, Any], settings_type: str) -> Dict[str, Any]:
        """Filter settings based on requested type"""
        if settings_type == 'all':
            return settings

        return {settings_type: settings.get('settings', {}).get(settings_type, {})}

    def _merge_settings(self, current: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """Merge current settings with updates"""
        settings = current.copy()
        for category, values in updates.items():
            if category in settings['settings']:
                settings['settings'][category].update(values)
            else:
                settings['settings'][category] = values

        # Update version info
        settings['version_info'] = {
            'settings_version': str(UUID()),
            'previous_version': settings['version_info'].get('settings_version'),
            'change_history': settings['version_info'].get('change_history', []) + [{
                'timestamp': datetime.utcnow().isoformat(),
                'changes': updates
            }]
        }

        return settings

    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings structure"""
        return {
            'settings': {
                'preferences': {},
                'appearance': {},
                'notifications': {},
                'privacy': {},
                'security': {}
            },
            'system_settings': {},
            'version_info': {
                'settings_version': str(UUID()),
                'previous_version': None,
                'change_history': []
            },
            'metadata': {
                'created_at': datetime.utcnow().isoformat()
            }
        }

    async def _handle_error(self, message: ProcessingMessage) -> None:
        """Handle settings-related errors"""
        error = message.content.get('error', 'Unknown error')
        self.logger.error(f"Settings error received: {error}")
        await self._notify_error(message, error)

    async def _notify_error(self, original_message: ProcessingMessage, error: str) -> None:
        """Notify about errors"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.SERVICE_ERROR,
                content={
                    'service': self.module_identifier.component_name,
                    'error': error,
                    'original_message': original_message.content
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager",
                    correlation_id=original_message.metadata.correlation_id
                )
            )
        )

    async def cleanup(self) -> None:
        """Cleanup service resources"""
        try:
            await self.message_broker.unsubscribe_all(
                self.module_identifier.component_name
            )
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")