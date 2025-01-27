# backend/core/services/staging_service.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ComponentType,
    ModuleIdentifier,
    MessageMetadata,
    ProcessingStage,
    ProcessingStatus,
    StagingContext
)

logger = logging.getLogger(__name__)


class StagingService:
    """
    Staging Service: Orchestrates staging workflows

    Responsibilities:
    - Coordinate between Staging Manager and Handler
    - Manage staging workflow logic
    - Route and transform messages
    - Track staging contexts
    """

    def __init__(self, message_broker: MessageBroker):
        # Core dependency
        self.message_broker = message_broker

        # Service identification
        self.module_identifier = ModuleIdentifier(
            component_name="staging_service",
            component_type=ComponentType.STAGING_SERVICE,
            department="staging",
            role="service"
        )

        # Active staging contexts
        self.active_contexts: Dict[str, StagingContext] = {}

        # Initialize message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Configure message handlers for staging service"""
        handlers = {
            # Manager Initiated Messages
            MessageType.STAGING_SERVICE_START: self._handle_service_start,
            MessageType.STAGING_SERVICE_UPDATE: self._handle_service_update,
            MessageType.STAGING_SERVICE_DECISION: self._handle_service_decision,

            # Handler Responses
            MessageType.STAGING_HANDLER_COMPLETE: self._handle_handler_complete,
            MessageType.STAGING_HANDLER_ERROR: self._handle_handler_error,
            MessageType.STAGING_HANDLER_STATUS: self._handle_handler_status,

            # Direct Staging Requests
            MessageType.STAGING_STORE_REQUEST: self._handle_store_request,
            MessageType.STAGING_RETRIEVE_REQUEST: self._handle_retrieve_request,
            MessageType.STAGING_DELETE_REQUEST: self._handle_delete_request,

            # Error Handling
            MessageType.STAGING_SERVICE_ERROR: self._handle_error
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=f"staging.{message_type.value}.*",
                callback=handler
            )

    async def _handle_service_start(self, message: ProcessingMessage) -> None:
        """
        Initialize staging workflow
        Triggered by Staging Manager
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            config = message.content.get('config', {})

            # Create staging context
            context = StagingContext(
                pipeline_id=pipeline_id,
                stage_type=ProcessingStage.INITIAL_VALIDATION
            )
            self.active_contexts[pipeline_id] = context

            # Forward to Staging Handler
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_HANDLER_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': config
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_store_request(self, message: ProcessingMessage) -> None:
        """
        Handle data storage requests
        Route to Staging Handler
        """
        try:
            # Generate unique stage ID if not provided
            stage_id = message.content.get('stage_id', str(uuid4()))

            # Forward to Staging Handler
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_HANDLER_STORE,
                    content={
                        'stage_id': stage_id,
                        **message.content
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_retrieve_request(self, message: ProcessingMessage) -> None:
        """
        Handle data retrieval requests
        Route to Staging Handler
        """
        try:
            stage_id = message.content.get('stage_id')

            # Forward to Staging Handler
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_HANDLER_RETRIEVE,
                    content=message.content,
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_delete_request(self, message: ProcessingMessage) -> None:
        """
        Handle deletion requests
        Route to Staging Handler
        """
        try:
            stage_id = message.content.get('stage_id')

            # Forward to Staging Handler
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_HANDLER_DELETE,
                    content=message.content,
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_handler_complete(self, message: ProcessingMessage) -> None:
        """
        Handle successful completion from Staging Handler
        Notify Staging Manager
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_contexts.get(pipeline_id)

            if context:
                # Update context
                context.status = ProcessingStatus.COMPLETED

                # Notify Staging Manager
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.STAGING_SERVICE_COMPLETE,
                        content={
                            'pipeline_id': pipeline_id,
                            'results': message.content
                        },
                        source_identifier=self.module_identifier
                    )
                )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_service_update(self, message: ProcessingMessage) -> None:
        """
        Handle update instructions from Staging Manager
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_contexts.get(pipeline_id)

            if context:
                # Forward update to Handler
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.STAGING_HANDLER_UPDATE,
                        content=message.content,
                        source_identifier=self.module_identifier
                    )
                )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_service_decision(self, message: ProcessingMessage) -> None:
        """
        Handle decision from Staging Manager
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            decision = message.content.get('decision')

            # Forward decision to Handler
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_HANDLER_DECISION,
                    content={
                        'pipeline_id': pipeline_id,
                        'decision': decision
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_handler_error(self, message: ProcessingMessage) -> None:
        """
        Handle errors from Staging Handler
        Notify Staging Manager
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            error = message.content.get('error')

            # Notify Staging Manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_SERVICE_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    async def _handle_handler_status(self, message: ProcessingMessage) -> None:
        """
        Handle status updates from Staging Handler
        """
        try:
            pipeline_id = message.content.get('pipeline_id')

            # Notify Staging Manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_SERVICE_STATUS,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': message.content.get('status')
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_error(
            self,
            original_message: ProcessingMessage,
            error: str
    ) -> None:
        """
        Centralized error handling
        """
        logger.error(f"Staging service error: {error}")

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.STAGING_SERVICE_ERROR,
                content={
                    'error': error,
                    'original_message': original_message.content
                },
                source_identifier=self.module_identifier
            )
        )

    async def cleanup(self) -> None:
        """
        Gracefully clean up service resources
        """
        try:
            # Unsubscribe from all message types
            await self.message_broker.unsubscribe(
                self.module_identifier.component_name
            )

            # Clear active contexts
            self.active_contexts.clear()

        except Exception as e:
            logger.error(f"Staging service cleanup failed: {str(e)}")