# backend/api/flask_app/pipeline/insight/advanced_analytics_service.py

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

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

def initialize_services(app):
    services = {
        'analytics_service': AnalyticsService(
            staging_manager=staging_manager,
            message_broker=message_broker,
            initialize_async=True
        )
    }
    return services


class AnalyticsService:
    """
    Service layer for advanced analytics functionality.
    Acts as message handler for analytics-related requests from CPM.
    """
    def __init__(self, staging_manager, message_broker, initialize_async=False):
        self.staging_manager = staging_manager
        self.message_broker = message_broker

        self.module_identifier = ModuleIdentifier(
            component_name="analytics_service",
            component_type=ComponentType.ANALYTICS_SERVICE,
            department="analytics",
            role="service"
        )

        self.logger = logger

        if initialize_async:
            asyncio.run(self._initialize_async())

    async def _initialize_async(self):
        await self._initialize_message_handlers()

    async def _initialize_message_handlers(self) -> None:
        handlers = {
            MessageType.ANALYTICS_START: self._handle_analytics_request,
            MessageType.ANALYTICS_STATUS_REQUEST: self._handle_status_request,
            MessageType.ANALYTICS_REPORT_REQUEST: self._handle_report_request,
            MessageType.ANALYTICS_ERROR: self._handle_error
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=f"analytics.{message_type.value}.#",
                callback=handler
            )

    def _setup_message_handlers(self) -> None:
        """Setup handlers for analytics-related messages"""
        handlers = {
            MessageType.ANALYTICS_REQUEST: self._handle_analytics_request,
            MessageType.ANALYTICS_STATUS_REQUEST: self._handle_status_request,
            MessageType.ANALYTICS_CONFIG_REQUEST: self._handle_config_request,
            MessageType.ANALYTICS_RESULT_REQUEST: self._handle_result_request,
            MessageType.ANALYTICS_ERROR: self._handle_error
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                component=self.module_identifier.component_name,
                pattern=f"analytics.{message_type.value}.#",
                callback=handler
            )

    async def _handle_analytics_request(self, message: ProcessingMessage) -> None:
        """Handle analytics request from CPM"""
        try:
            control_point_id = message.content.get('control_point_id')
            request_data = message.content.get('request_data', {})

            # Store in staging
            staged_id = await self.staging_manager.store_incoming_data(
                pipeline_id=request_data.get('pipeline_id'),
                data=request_data,
                source_type='advanced_analytics',
                metadata={
                    'control_point_id': control_point_id,
                    'type': 'analytics_request',
                    'config': request_data.get('config', {})
                }
            )

            # Forward to analytics manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_START,
                    content={
                        'pipeline_id': request_data.get('pipeline_id'),
                        'staged_id': staged_id,
                        'config': request_data.get('config', {}),
                        'control_point_id': control_point_id
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="advanced_analytics_manager",
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle analytics request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_status_request(self, message: ProcessingMessage) -> None:
        """Handle analytics status request"""
        try:
            staged_id = message.content.get('staged_id')

            # Get staged data
            staged_data = await self.staging_manager.retrieve_data(
                staged_id,
                'ANALYTICS'
            )
            if not staged_data:
                raise ValueError(f"Analytics process {staged_id} not found")

            # Send status response
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_STATUS_RESPONSE,
                    content={
                        'staged_id': staged_id,
                        'status': staged_data.get('status', 'unknown'),
                        'phase': staged_data.get('phase'),
                        'progress': staged_data.get('progress', 0),
                        'current_module': staged_data.get('current_module'),
                        'created_at': staged_data.get('created_at'),
                        'error': staged_data.get('error')
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component=message.metadata.source_component,
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle status request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_config_request(self, message: ProcessingMessage) -> None:
        """Handle analytics configuration request"""
        try:
            staged_id = message.content.get('staged_id')
            config_updates = message.content.get('config_updates', {})

            # Forward to analytics manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_CONFIG_UPDATE,
                    content={
                        'staged_id': staged_id,
                        'config_updates': config_updates,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="advanced_analytics_manager",
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle config request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_result_request(self, message: ProcessingMessage) -> None:
        """Handle analytics result request"""
        try:
            staged_id = message.content.get('staged_id')

            # Get staged data
            staged_data = await self.staging_manager.retrieve_data(
                staged_id,
                'ANALYTICS'
            )
            if not staged_data:
                raise ValueError(f"Analytics process {staged_id} not found")

            # Send result response
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_RESULT_RESPONSE,
                    content={
                        'staged_id': staged_id,
                        'results': staged_data.get('results', {}),
                        'models': staged_data.get('models', {}),
                        'metrics': staged_data.get('metrics', {}),
                        'metadata': staged_data.get('metadata', {}),
                        'created_at': staged_data.get('created_at')
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component=message.metadata.source_component,
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle result request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_error(self, message: ProcessingMessage) -> None:
        """Handle analytics-related errors"""
        error = message.content.get('error', 'Unknown error')
        self.logger.error(f"Analytics error received: {error}")

        await self._notify_error(message, error)

    async def _notify_error(self, original_message: ProcessingMessage, error: str) -> None:
        """Notify CPM about errors"""
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
            # Unsubscribe from message broker topics
            await self.message_broker.unsubscribe_all(
                self.module_identifier.component_name
            )
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")