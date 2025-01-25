# backend/api/flask_app/pipeline/decisions/decision_service.py

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
        'decision_service': DecisionService(
            staging_manager=staging_manager,
            message_broker=message_broker,
            initialize_async=True
        )
    }
    return services

class DecisionService:
    """
    Service layer for decision functionality.
    Acts as message handler for decision-related requests from CPM.
    """
    def __init__(self, staging_manager, message_broker, initialize_async=False):
        self.staging_manager = staging_manager
        self.message_broker = message_broker

        self.module_identifier = ModuleIdentifier(
            component_name="decision_service",
            component_type=ComponentType.DECISION_SERVICE,
            department="decision",
            role="service"
        )

        self.logger = logger

        if initialize_async:
            asyncio.run(self._initialize_async())

    async def _initialize_async(self):
        await self._initialize_message_handlers()

    async def _initialize_message_handlers(self) -> None:

        handlers = {
            MessageType.DECISION_REQUEST: self._handle_decision_request,
            MessageType.DECISION_STATUS_REQUEST: self._handle_status_request,
            MessageType.DECISION_SUBMIT_REQUEST: self._handle_submit_request,
            MessageType.DECISION_FEEDBACK_REQUEST: self._handle_feedback_request,
            MessageType.DECISION_ERROR: self._handle_error
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=f"decision.{message_type.value}.#",
                callback=handler
            )

    def _setup_message_handlers(self) -> None:
        """Setup handlers for decision-related messages"""
        handlers = {
            MessageType.DECISION_REQUEST: self._handle_decision_request,
            MessageType.DECISION_STATUS_REQUEST: self._handle_status_request,
            MessageType.DECISION_SUBMIT_REQUEST: self._handle_submit_request,
            MessageType.DECISION_FEEDBACK_REQUEST: self._handle_feedback_request,
            MessageType.DECISION_ERROR: self._handle_error
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                component=self.module_identifier.component_name,
                pattern=f"decision.{message_type.value}.#",
                callback=handler
            )

    async def _handle_decision_request(self, message: ProcessingMessage) -> None:
        """Handle new decision request from CPM"""
        try:
            control_point_id = message.content.get('control_point_id')
            request_data = message.content.get('request_data', {})

            # Store in staging
            staged_id = await self.staging_manager.store_incoming_data(
                pipeline_id=request_data.get('pipeline_id'),
                data=request_data,
                source_type='decision_processing',
                metadata={
                    'control_point_id': control_point_id,
                    'type': 'decision_request',
                    'options': request_data.get('options', []),
                    'impacts': request_data.get('impacts', {})
                }
            )

            # Forward to decision manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_START,
                    content={
                        'pipeline_id': request_data.get('pipeline_id'),
                        'staged_id': staged_id,
                        'decision_type': request_data.get('decision_type'),
                        'options': request_data.get('options', []),
                        'impacts': request_data.get('impacts', {}),
                        'constraints': request_data.get('constraints', {}),
                        'control_point_id': control_point_id
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="decision_manager",
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle decision request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_status_request(self, message: ProcessingMessage) -> None:
        """Handle decision status request"""
        try:
            staged_id = message.content.get('staged_id')

            # Get staged data
            staged_data = await self.staging_manager.retrieve_data(
                staged_id,
                'DECISION'
            )
            if not staged_data:
                raise ValueError(f"Decision {staged_id} not found")

            # Send status response
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_STATUS_RESPONSE,
                    content={
                        'staged_id': staged_id,
                        'status': staged_data.get('status', 'unknown'),
                        'phase': staged_data.get('phase'),
                        'pending_count': staged_data.get('pending_count', 0),
                        'completed_count': staged_data.get('completed_count', 0),
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

    async def _handle_submit_request(self, message: ProcessingMessage) -> None:
        """Handle decision submission request"""
        try:
            staged_id = message.content.get('staged_id')
            decision_data = message.content.get('decision', {})

            # Forward to decision manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_SUBMIT,
                    content={
                        'staged_id': staged_id,
                        'decision': decision_data,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="decision_manager",
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle submit request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_feedback_request(self, message: ProcessingMessage) -> None:
        """Handle decision feedback request"""
        try:
            staged_id = message.content.get('staged_id')
            feedback_data = message.content.get('feedback', {})

            # Store feedback in staging
            await self.staging_manager.store_component_output(
                staged_id=staged_id,
                component_type='DECISION',
                output={'feedback': feedback_data},
                metadata={
                    'update_type': 'feedback',
                    'timestamp': datetime.utcnow().isoformat()
                }
            )

            # Notify decision manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_FEEDBACK,
                    content={
                        'staged_id': staged_id,
                        'feedback': feedback_data,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="decision_manager",
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle feedback request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_error(self, message: ProcessingMessage) -> None:
        """Handle decision-related errors"""
        error = message.content.get('error', 'Unknown error')
        self.logger.error(f"Decision error received: {error}")

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