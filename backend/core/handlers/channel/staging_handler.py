# backend/core/handlers/channel/staging_handler.py

import logging
from typing import Dict, Any, Optional

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ComponentType,
    ModuleIdentifier,
    MessageMetadata
)

logger = logging.getLogger(__name__)


class StagingHandler:
    """
    Staging Handler: Pure message routing and transformation layer

    Responsibilities:
    - Route staging-related messages
    - Perform lightweight message transformations
    - Ensure message consistency
    - Minimal business logic
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        # Handler identification
        self.module_identifier = ModuleIdentifier(
            component_name="staging_handler",
            component_type=ComponentType.STAGING_HANDLER,
            department="staging",
            role="handler"
        )

        # Initialize message routing
        self._setup_message_handlers()

    async def _setup_message_handlers(self) -> None:
        """Configure message routing table"""
        routing_map = {
            # Service Layer Messages
            MessageType.STAGING_HANDLER_START: self._route_start_request,
            MessageType.STAGING_HANDLER_STORE: self._route_store_request,
            MessageType.STAGING_HANDLER_RETRIEVE: self._route_retrieve_request,
            MessageType.STAGING_HANDLER_DELETE: self._route_delete_request,
            MessageType.STAGING_HANDLER_UPDATE: self._route_update_request,
            MessageType.STAGING_HANDLER_DECISION: self._route_decision_request,

            # Error Handling
            MessageType.STAGING_ERROR: self._handle_error_routing
        }

        # Subscribe to all routing patterns
        for message_type, handler in routing_map.items():
            await self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=f"staging.{message_type.value}.*",
                callback=handler
            )

    async def _route_start_request(self, message: ProcessingMessage) -> None:
        """Route staging process start request"""
        try:
            # Validate and preprocess message
            transformed_message = self._preprocess_message(message)

            # Route to staging processor
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_PROCESSOR_START,
                    content=transformed_message.content,
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    async def _route_store_request(self, message: ProcessingMessage) -> None:
        """Route data storage requests"""
        try:
            transformed_message = self._preprocess_message(message)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_PROCESSOR_STORE,
                    content=transformed_message.content,
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    async def _route_retrieve_request(self, message: ProcessingMessage) -> None:
        """Route data retrieval requests"""
        try:
            transformed_message = self._preprocess_message(message)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_PROCESSOR_RETRIEVE,
                    content=transformed_message.content,
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    async def _route_delete_request(self, message: ProcessingMessage) -> None:
        """Route deletion requests"""
        try:
            transformed_message = self._preprocess_message(message)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_PROCESSOR_DELETE,
                    content=transformed_message.content,
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    async def _route_update_request(self, message: ProcessingMessage) -> None:
        """Route update requests"""
        try:
            transformed_message = self._preprocess_message(message)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_PROCESSOR_UPDATE,
                    content=transformed_message.content,
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    async def _route_decision_request(self, message: ProcessingMessage) -> None:
        """Route decision requests"""
        try:
            transformed_message = self._preprocess_message(message)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_PROCESSOR_DECISION,
                    content=transformed_message.content,
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    async def _handle_error_routing(self, message: ProcessingMessage) -> None:
        """
        Centralized error routing mechanism

        - Log errors
        - Publish to error tracking system
        - Potential retry or escalation
        """
        try:
            logger.error(f"Staging handler error: {message.content}")

            # Publish to centralized error tracking
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.SYSTEM_ERROR,
                    content={
                        'error_source': 'staging_handler',
                        'original_message': message.content
                    },
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            logger.critical(f"Error handling failed: {str(e)}")

    def _preprocess_message(self, message: ProcessingMessage) -> ProcessingMessage:
        """
        Perform lightweight message preprocessing

        - Validate required fields
        - Normalize message structure
        - Add routing metadata
        """
        required_fields = ['stage_id']

        # Validate presence of required fields
        for field in required_fields:
            if field not in message.content:
                raise ValueError(f"Missing required field: {field}")

        # Normalize and enrich message
        message.metadata.routing_path.append(self.module_identifier)

        return message

    async def _publish_routing_error(
            self,
            original_message: ProcessingMessage,
            error: str
    ) -> None:
        """
        Publish routing-specific errors

        - Standardized error reporting
        - Preserves original message context
        """
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.STAGING_ERROR,
                content={
                    'error': error,
                    'original_message': original_message.content
                },
                source_identifier=self.module_identifier
            )
        )

    async def cleanup(self) -> None:
        """
        Gracefully unsubscribe from all message broker topics
        """
        try:
            await self.message_broker.unsubscribe_all(
                self.module_identifier.component_name
            )
        except Exception as e:
            logger.error(f"Staging handler cleanup failed: {str(e)}")