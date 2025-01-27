# backend/core/handlers/channel/insight_handler.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ComponentType,
    ModuleIdentifier,
    MessageMetadata,
    ProcessingStage,
    ProcessingStatus,
    InsightContext,
    InsightState
)

logger = logging.getLogger(__name__)


class InsightHandler:
    """
    Insight Handler: Pure message routing between Service and Processor.
    No business logic, only message transformation and routing.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        # Handler identification
        self.module_identifier = ModuleIdentifier(
            component_name="insight_handler",
            component_type=ComponentType.INSIGHT_HANDLER,
            department="insight",
            role="handler"
        )

        # Initialize message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup message routing handlers"""
        routing_map = {
            # Service Messages
            MessageType.INSIGHT_HANDLER_START: self._route_start_request,
            MessageType.INSIGHT_HANDLER_UPDATE: self._route_update_request,
            MessageType.INSIGHT_HANDLER_VALIDATE: self._route_validate_request,

            # Processor Responses
            MessageType.INSIGHT_PROCESSOR_COMPLETE: self._route_processor_complete,
            MessageType.INSIGHT_PROCESSOR_ERROR: self._route_processor_error,
            MessageType.INSIGHT_PROCESSOR_STATUS: self._route_processor_status,

            # Error Handling
            MessageType.INSIGHT_ERROR: self._handle_error_routing
        }

        for message_type, handler in routing_map.items():
            self.message_broker.subscribe(
                self.module_identifier,
                f"insight.{message_type.value}.#",
                handler
            )

    async def _route_start_request(self, message: ProcessingMessage) -> None:
        """Route start request to processor"""
        try:
            # Validate and transform message
            transformed_message = self._preprocess_message(message)

            # Route to processor
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_PROCESSOR_START,
                    content=transformed_message.content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="insight_processor",
                        domain_type="insight",
                        processing_stage=ProcessingStage.INSIGHT_GENERATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    async def _route_update_request(self, message: ProcessingMessage) -> None:
        """Route update request to processor"""
        try:
            transformed_message = self._preprocess_message(message)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_PROCESSOR_UPDATE,
                    content=transformed_message.content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="insight_processor",
                        domain_type="insight",
                        processing_stage=ProcessingStage.INSIGHT_GENERATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    async def _route_processor_complete(self, message: ProcessingMessage) -> None:
        """Route processor completion to service"""
        try:
            transformed_message = self._preprocess_message(message)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_HANDLER_COMPLETE,
                    content=transformed_message.content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="insight_service",
                        domain_type="insight",
                        processing_stage=ProcessingStage.INSIGHT_GENERATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    async def _route_processor_status(self, message: ProcessingMessage) -> None:
        """Route processor status update to service"""
        try:
            transformed_message = self._preprocess_message(message)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_HANDLER_STATUS,
                    content=transformed_message.content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="insight_service",
                        domain_type="insight",
                        processing_stage=ProcessingStage.INSIGHT_GENERATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    async def _route_processor_error(self, message: ProcessingMessage) -> None:
        """Route processor error to service"""
        try:
            transformed_message = self._preprocess_message(message)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_HANDLER_ERROR,
                    content=transformed_message.content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="insight_service",
                        domain_type="insight",
                        processing_stage=ProcessingStage.INSIGHT_GENERATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    def _preprocess_message(self, message: ProcessingMessage) -> ProcessingMessage:
        """
        Preprocess message for routing
        Validate required fields and normalize structure
        """
        required_fields = ['pipeline_id']

        # Validate message content
        for field in required_fields:
            if field not in message.content:
                raise ValueError(f"Missing required field: {field}")

        # Add routing metadata
        if not message.metadata:
            message.metadata = MessageMetadata()

        message.metadata.domain_type = "insight"
        message.metadata.processing_stage = ProcessingStage.INSIGHT_GENERATION

        return message

    async def _publish_routing_error(
            self,
            original_message: ProcessingMessage,
            error: str
    ) -> None:
        """Publish routing error"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.INSIGHT_ERROR,
                content={
                    'error': error,
                    'original_message': original_message.content,
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="insight_service",
                    domain_type="insight",
                    processing_stage=ProcessingStage.INSIGHT_GENERATION
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_error_routing(self, message: ProcessingMessage) -> None:
        """Centralized error routing"""
        logger.error(f"Routing error: {message.content}")

        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.SYSTEM_ERROR,
                    content={
                        'error_source': 'insight_handler',
                        'original_message': message.content,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="error_handler",
                        domain_type="insight"
                    ),
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            logger.critical(f"Error handling failed: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup handler resources"""
        try:
            # Unsubscribe from all patterns
            await self.message_broker.unsubscribe_all(
                self.module_identifier.component_name
            )
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise