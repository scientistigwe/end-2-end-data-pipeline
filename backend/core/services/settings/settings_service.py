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
    MessageMetadata,
    ProcessingStage,
    ProcessingStatus
)

logger = logging.getLogger(__name__)

class SettingsService:
    """
    Settings Service managing settings through message-driven, unidirectional communication
    Responsible for processing settings-related messages without direct dependencies
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        self.module_identifier = ModuleIdentifier(
            component_name="settings_service",
            component_type=ComponentType.SETTINGS_SERVICE,
            department="settings",
            role="service"
        )

        # Track processing requests
        self.active_requests: Dict[str, Dict[str, Any]] = {}

        # Initialize message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup subscriptions for settings-related messages"""
        handlers = {
            MessageType.SETTINGS_REQUEST: self._handle_settings_request,
            MessageType.SETTINGS_UPDATE: self._handle_settings_update,
            MessageType.SETTINGS_RESET: self._handle_settings_reset,
            MessageType.SYSTEM_SETTINGS_REQUEST: self._handle_system_settings_request,
            MessageType.SETTINGS_CONFIG_UPDATE: self._handle_config_update
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_settings_request(self, message: ProcessingMessage) -> None:
        """
        Handle settings request through message-driven approach
        No direct interaction with staging or other components
        """
        try:
            pipeline_id = message.content.get('pipeline_id') or str(UUID())
            user_id = message.content.get('user_id')
            settings_type = message.content.get('settings_type', 'all')

            # Prepare response message
            response_message = ProcessingMessage(
                message_type=MessageType.SETTINGS_RESPONSE,
                content={
                    'pipeline_id': pipeline_id,
                    'user_id': user_id,
                    'settings_type': settings_type,
                    'settings': self._get_default_settings(),
                    'timestamp': datetime.utcnow().isoformat()
                },
                source_identifier=self.module_identifier,
                target_identifier=message.source_identifier,
                metadata=MessageMetadata(
                    correlation_id=message.metadata.correlation_id,
                    source_component=self.module_identifier.component_name,
                    processing_stage=ProcessingStage.SETTINGS_MANAGEMENT
                )
            )

            # Publish response through message broker
            await self.message_broker.publish(response_message)

        except Exception as e:
            await self._publish_error(
                pipeline_id=message.content.get('pipeline_id'),
                error=str(e),
                original_message=message
            )

    async def _handle_settings_update(self, message: ProcessingMessage) -> None:
        """
        Handle settings update through message-driven approach
        """
        try:
            pipeline_id = message.content.get('pipeline_id') or str(UUID())
            user_id = message.content.get('user_id')
            update_data = message.content.get('settings', {})

            # Prepare update response message
            response_message = ProcessingMessage(
                message_type=MessageType.SETTINGS_UPDATE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'user_id': user_id,
                    'settings': self._merge_settings(
                        self._get_default_settings(),
                        update_data
                    ),
                    'timestamp': datetime.utcnow().isoformat()
                },
                source_identifier=self.module_identifier,
                target_identifier=message.source_identifier,
                metadata=MessageMetadata(
                    correlation_id=message.metadata.correlation_id,
                    source_component=self.module_identifier.component_name,
                    processing_stage=ProcessingStage.SETTINGS_MANAGEMENT
                )
            )

            # Publish response through message broker
            await self.message_broker.publish(response_message)

        except Exception as e:
            await self._publish_error(
                pipeline_id=message.content.get('pipeline_id'),
                error=str(e),
                original_message=message
            )

    async def _publish_error(
        self,
        pipeline_id: Optional[str],
        error: str,
        original_message: Optional[ProcessingMessage] = None
    ) -> None:
        """
        Publish error message through message broker
        """
        error_message = ProcessingMessage(
            message_type=MessageType.SERVICE_ERROR,
            content={
                'pipeline_id': pipeline_id,
                'service': self.module_identifier.component_name,
                'error': error,
                'original_message': original_message.content if original_message else {}
            },
            source_identifier=self.module_identifier,
            metadata=MessageMetadata(
                processing_stage=ProcessingStage.ERROR_HANDLING
            )
        )

        await self.message_broker.publish(error_message)

    def _get_default_settings(self) -> Dict[str, Any]:
        """
        Generate default settings
        In production, this might fetch from a configuration service
        """
        return {
            'preferences': {},
            'appearance': {},
            'notifications': {},
            'privacy': {},
            'security': {},
            'version_info': {
                'version': str(UUID()),
                'created_at': datetime.utcnow().isoformat()
            }
        }

    def _merge_settings(
        self,
        current_settings: Dict[str, Any],
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge current settings with update data"""
        merged = current_settings.copy()
        for category, values in update_data.items():
            if category in merged:
                merged[category].update(values)
            else:
                merged[category] = values

        merged['version_info']['updated_at'] = datetime.utcnow().isoformat()
        return merged

    async def _handle_system_settings_request(self, message: ProcessingMessage) -> None:
        """Handle system-wide settings request"""
        system_settings_message = ProcessingMessage(
            message_type=MessageType.SYSTEM_SETTINGS_RESPONSE,
            content={
                'system_settings': {},  # Placeholder for system-wide settings
                'timestamp': datetime.utcnow().isoformat()
            },
            source_identifier=self.module_identifier,
            target_identifier=message.source_identifier,
            metadata=MessageMetadata(
                correlation_id=message.metadata.correlation_id,
                processing_stage=ProcessingStage.SETTINGS_MANAGEMENT
            )
        )
        await self.message_broker.publish(system_settings_message)

    async def _handle_config_update(self, message: ProcessingMessage) -> None:
        """Handle configuration update request"""
        config_update_message = ProcessingMessage(
            message_type=MessageType.SETTINGS_CONFIG_UPDATE_COMPLETE,
            content={
                'status': 'updated',
                'timestamp': datetime.utcnow().isoformat()
            },
            source_identifier=self.module_identifier,
            target_identifier=message.source_identifier,
            metadata=MessageMetadata(
                correlation_id=message.metadata.correlation_id,
                processing_stage=ProcessingStage.SETTINGS_MANAGEMENT
            )
        )
        await self.message_broker.publish(config_update_message)

    async def cleanup(self) -> None:
        """Cleanup service resources"""
        try:
            # Unsubscribe from message broker
            await self.message_broker.unsubscribe_all(self.module_identifier)
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")