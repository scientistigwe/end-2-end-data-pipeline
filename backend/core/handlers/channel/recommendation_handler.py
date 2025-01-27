# backend/core/handlers/channel/recommendation_handler.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ComponentType,
    ModuleIdentifier,
    MessageMetadata,
    ProcessingStage,
    ProcessingStatus,
    RecommendationState
)

logger = logging.getLogger(__name__)


class RecommendationHandler:
    """
    Recommendation Handler: Pure message routing layer.
    - Routes between Service and Processor
    - Performs message transformations
    - No business logic
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        # Handler identification
        self.module_identifier = ModuleIdentifier(
            component_name="recommendation_handler",
            component_type=ComponentType.RECOMMENDATION_HANDLER,
            department="recommendation",
            role="handler"
        )

        # Setup message routing
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup message routing handlers"""
        routing_map = {
            # Service Messages
            MessageType.RECOMMENDATION_HANDLER_START: self._route_start_request,
            MessageType.RECOMMENDATION_HANDLER_UPDATE: self._route_update_request,
            MessageType.RECOMMENDATION_HANDLER_FILTER: self._route_filter_request,
            MessageType.RECOMMENDATION_HANDLER_RANK: self._route_rank_request,
            MessageType.RECOMMENDATION_HANDLER_VALIDATE: self._route_validate_request,

            # Processor Responses
            MessageType.RECOMMENDATION_PROCESSOR_COMPLETE: self._route_processor_complete,
            MessageType.RECOMMENDATION_PROCESSOR_ERROR: self._route_processor_error,
            MessageType.RECOMMENDATION_PROCESSOR_STATUS: self._route_processor_status,

            # Engine Messages
            MessageType.RECOMMENDATION_ENGINE_RESPONSE: self._route_engine_response,
            MessageType.RECOMMENDATION_ENGINE_ERROR: self._route_engine_error,

            # Error Handling
            MessageType.RECOMMENDATION_ERROR: self._handle_error_routing
        }

        for message_type, handler in routing_map.items():
            self.message_broker.subscribe(
                self.module_identifier,
                f"recommendation.{message_type.value}.#",
                handler
            )

    async def _route_start_request(self, message: ProcessingMessage) -> None:
        """Route start request to processor"""
        try:
            # Transform message
            transformed_message = self._preprocess_message(message)

            # Route to processor
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_PROCESSOR_START,
                    content=transformed_message.content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="recommendation_processor",
                        domain_type="recommendation",
                        processing_stage=ProcessingStage.RECOMMENDATION
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
                    message_type=MessageType.RECOMMENDATION_HANDLER_COMPLETE,
                    content=transformed_message.content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="recommendation_service",
                        domain_type="recommendation",
                        processing_stage=ProcessingStage.RECOMMENDATION
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
                    message_type=MessageType.RECOMMENDATION_HANDLER_STATUS,
                    content=transformed_message.content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="recommendation_service",
                        domain_type="recommendation",
                        processing_stage=ProcessingStage.RECOMMENDATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    async def _route_engine_response(self, message: ProcessingMessage) -> None:
        """Route engine response to processor"""
        try:
            transformed_message = self._preprocess_message(message)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_PROCESSOR_ENGINE_RESPONSE,
                    content=transformed_message.content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="recommendation_processor",
                        domain_type="recommendation",
                        processing_stage=ProcessingStage.RECOMMENDATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    def _preprocess_message(self, message: ProcessingMessage) -> ProcessingMessage:
        """
        Preprocess message for routing
        - Validate required fields
        - Normalize message structure
        - Add routing metadata
        """
        required_fields = ['pipeline_id']

        # Validate message content
        for field in required_fields:
            if field not in message.content:
                raise ValueError(f"Missing required field: {field}")

        # Add routing metadata
        if not message.metadata:
            message.metadata = MessageMetadata()

        message.metadata.domain_type = "recommendation"
        message.metadata.processing_stage = ProcessingStage.RECOMMENDATION

        return message

    async def _publish_routing_error(
            self,
            original_message: ProcessingMessage,
            error: str
    ) -> None:
        """Publish routing error"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.RECOMMENDATION_ERROR,
                content={
                    'error': error,
                    'original_message': original_message.content,
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="recommendation_service",
                    domain_type="recommendation",
                    processing_stage=ProcessingStage.RECOMMENDATION
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_error_routing(self, message: ProcessingMessage) -> None:
        """Handle error routing"""
        logger.error(f"Routing error: {message.content}")

        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.SYSTEM_ERROR,
                    content={
                        'error_source': 'recommendation_handler',
                        'original_message': message.content,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="error_handler",
                        domain_type="recommendation"
                    ),
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            logger.critical(f"Error handling failed: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup handler resources"""
        try:
            # Unsubscribe from all message patterns
            await self.message_broker.unsubscribe_all(
                self.module_identifier.component_name
            )
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise