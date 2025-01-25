# backend/api/flask_app/pipeline/insight/insight_service.py

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
    from asyncio import run as asyncio_run

    services = {
        'insight_service': InsightService(
            staging_manager=staging_manager,
            message_broker=message_broker,
            initialize_async=True
        )
    }

    return services


class InsightService:
    """
    Service layer for insight generation functionality.
    Acts as message handler for insight-related requests from CPM.
    """

    def __init__(self, staging_manager, message_broker, initialize_async=False):
        self.staging_manager = staging_manager
        self.message_broker = message_broker

        self.module_identifier = ModuleIdentifier(
            component_name="insight_service",
            component_type=ComponentType.INSIGHT_SERVICE,
            department="insight",
            role="service"
        )

        self.logger = logger

        # Optional async initialization
        if initialize_async:
            asyncio.run(self._initialize_async())

    async def _initialize_async(self):
        await self._initialize_message_handlers()

    async def _initialize_message_handlers(self) -> None:
        """Setup handlers for insight-related messages"""
        handlers = {
            MessageType.INSIGHT_START: self._handle_insight_request,
            MessageType.INSIGHT_STATUS_REQUEST: self._handle_status_request,
            MessageType.INSIGHT_REPORT_REQUEST: self._handle_report_request,
            MessageType.INSIGHT_REVIEW_REQUEST: self._handle_review_request,
            MessageType.INSIGHT_ERROR: self._handle_error
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=f"insight.{message_type.value}.#",
                callback=handler
            )

    async def _handle_insight_request(self, message: ProcessingMessage) -> None:
        """Handle insight generation request from CPM"""
        try:
            control_point_id = message.content.get('control_point_id')
            request_data = message.content.get('request_data', {})

            # Store in staging
            staged_id = await self.staging_manager.store_incoming_data(
                request_data.get('pipeline_id'),
                request_data,
                source_type='insight_generation',
                metadata={
                    'control_point_id': control_point_id,
                    'type': 'insight_request'
                },
            )

            # Forward to insight manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_START,
                    content={
                        'pipeline_id': request_data.get('pipeline_id'),
                        'staged_id': staged_id,
                        'config': request_data.get('config', {}),
                        'control_point_id': control_point_id
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="insight_manager",
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle insight request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_status_request(self, message: ProcessingMessage) -> None:
        """Handle insight status request"""
        try:
            staged_id = message.content.get('staged_id')

            # Get staged data
            staged_data = await self.staging_manager.retrieve_data(
                staged_id,
                'INSIGHT'
            )
            if not staged_data:
                raise ValueError(f"Analysis {staged_id} not found")

            # Send status response
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_STATUS_RESPONSE,
                    content={
                        'staged_id': staged_id,
                        'status': staged_data.get('status', 'unknown'),
                        'phase': staged_data.get('phase'),
                        'insights_generated': staged_data.get('insights_generated', 0),
                        'insights_validated': staged_data.get('insights_validated', 0),
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

    async def _handle_review_request(self, message: ProcessingMessage) -> None:
        """Handle insight review request"""
        try:
            staged_id = message.content.get('staged_id')
            decisions = message.content.get('decisions', {})

            # Forward review to manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_REVIEW,
                    content={
                        'staged_id': staged_id,
                        'decisions': decisions,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="insight_manager",
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle review request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_report_request(self, message: ProcessingMessage) -> None:
        """Handle insight report request"""
        try:
            staged_id = message.content.get('staged_id')

            # Get staged data
            staged_data = await self.staging_manager.retrieve_data(
                staged_id,
                'INSIGHT'
            )
            if not staged_data:
                raise ValueError(f"Analysis {staged_id} not found")

            # Send report response
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_REPORT_RESPONSE,
                    content={
                        'staged_id': staged_id,
                        'pipeline_id': staged_data.get('pipeline_id'),
                        'insights': staged_data.get('insights', []),
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
            self.logger.error(f"Failed to handle report request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_error(self, message: ProcessingMessage) -> None:
        """Handle insight-related errors"""
        error = message.content.get('error', 'Unknown error')
        self.logger.error(f"Insight error received: {error}")

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