# backend/core/managers/staging_manager.py

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ComponentType,
    ModuleIdentifier,
    MessageMetadata,
    ProcessingStage,
    ProcessingStatus,
    StagingContext,
    StagingState
)

logger = logging.getLogger(__name__)


class StagingManager:
    """
    Staging Manager: Coordinates staging workflows via message-driven communication

    Responsibilities:
    - Subscribe to Control Point Manager messages
    - Manage high-level staging process state
    - Route staging-related messages
    - Track active staging processes
    """

    def __init__(self, message_broker: MessageBroker):
        # Core dependency
        self.message_broker = message_broker

        # Manager identification
        self.module_identifier = ModuleIdentifier(
            component_name="staging_manager",
            component_type=ComponentType.STAGING_MANAGER,
            department="staging",
            role="manager"
        )

        # Active staging contexts
        self.active_contexts: Dict[str, StagingContext] = {}

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Configure message handlers for staging manager"""
        # Message type subscriptions
        handlers = {
            # Control Point Manager Messages
            MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
            MessageType.CONTROL_POINT_UPDATED: self._handle_control_point_updated,
            MessageType.CONTROL_POINT_DECISION: self._handle_control_point_decision,

            # Service Layer Messages
            MessageType.STAGING_SERVICE_START: self._handle_service_start,
            MessageType.STAGING_SERVICE_STATUS: self._handle_service_status,
            MessageType.STAGING_SERVICE_COMPLETE: self._handle_service_complete,
            MessageType.STAGING_SERVICE_ERROR: self._handle_service_error
        }

        # Subscribe to all relevant message types
        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=message_type.value,
                callback=handler
            )

    async def _handle_control_point_created(self, message: ProcessingMessage) -> None:
        """
        Handle new control point for staging
        Initiate staging workflow based on message
        """
        try:
            pipeline_id = message.content['pipeline_id']
            config = message.content.get('config', {})

            # Create staging context
            context = StagingContext(
                pipeline_id=pipeline_id,
                stage_type=ProcessingStage.INITIAL_VALIDATION,
                status=ProcessingStatus.PENDING
            )
            self.active_contexts[pipeline_id] = context

            # Publish service start message
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_SERVICE_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': config
                    },
                    source_identifier=self.module_identifier,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="staging_service"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Control point handling failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_control_point_updated(self, message: ProcessingMessage) -> None:
        """Handle updates to control point"""
        try:
            pipeline_id = message.content['pipeline_id']
            context = self.active_contexts.get(pipeline_id)

            if context:
                # Update context
                context.status = message.content.get('status', context.status)

                # Publish service update message
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.STAGING_SERVICE_UPDATE,
                        content={
                            'pipeline_id': pipeline_id,
                            'update': message.content
                        },
                        source_identifier=self.module_identifier
                    )
                )

        except Exception as e:
            logger.error(f"Control point update failed: {str(e)}")

    async def _handle_control_point_decision(self, message: ProcessingMessage) -> None:
        """Handle decisions about staging process"""
        try:
            pipeline_id = message.content['pipeline_id']
            decision = message.content['decision']

            # Publish service decision message
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_SERVICE_DECISION,
                    content={
                        'pipeline_id': pipeline_id,
                        'decision': decision
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Control point decision handling failed: {str(e)}")

    async def _handle_service_start(self, message: ProcessingMessage) -> None:
        """Handle service start notification"""
        pipeline_id = message.content.get('pipeline_id')

        # Update context state
        context = self.active_contexts.get(pipeline_id)
        if context:
            context.state = StagingState.INITIALIZING

    async def _handle_service_status(self, message: ProcessingMessage) -> None:
        """Handle status updates from service"""
        pipeline_id = message.content.get('pipeline_id')

        # Publish status update message
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_STAGE_STATUS_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.INITIAL_VALIDATION,
                    'status': message.content
                },
                source_identifier=self.module_identifier
            )
        )

    async def _handle_service_complete(self, message: ProcessingMessage) -> None:
        """Handle successful service completion"""
        pipeline_id = message.content.get('pipeline_id')

        # Update context
        context = self.active_contexts.get(pipeline_id)
        if context:
            context.state = StagingState.STORED

        # Publish stage complete message
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_STAGE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.INITIAL_VALIDATION,
                    'results': message.content
                },
                source_identifier=self.module_identifier
            )
        )

    async def _handle_service_error(self, message: ProcessingMessage) -> None:
        """Handle errors from service"""
        pipeline_id = message.content.get('pipeline_id')
        error = message.content.get('error')

        # Update context
        context = self.active_contexts.get(pipeline_id)
        if context:
            context.state = StagingState.ERROR

        # Publish error message
        await self._publish_error(pipeline_id, error)

    async def _publish_error(self, pipeline_id: str, error: str) -> None:
        """Publish error message"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.INITIAL_VALIDATION,
                    'error': error
                },
                source_identifier=self.module_identifier
            )
        )

    async def cleanup(self) -> None:
        """Clean up manager resources"""
        try:
            # Publish cleanup messages for active contexts
            for pipeline_id in list(self.active_contexts.keys()):
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.PIPELINE_STAGE_COMPLETE,
                        content={
                            'pipeline_id': pipeline_id,
                            'stage': ProcessingStage.INITIAL_VALIDATION,
                            'status': 'cleaned'
                        },
                        source_identifier=self.module_identifier
                    )
                )
                del self.active_contexts[pipeline_id]

        except Exception as e:
            logger.error(f"Staging manager cleanup failed: {str(e)}")