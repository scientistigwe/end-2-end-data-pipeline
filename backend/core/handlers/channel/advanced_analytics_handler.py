# backend/core/handlers/channel/analytics_handler.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    ModuleIdentifier,
    ComponentType,
    ProcessingStage,
    AnalyticsContext
)
from ..base.base_handler import BaseChannelHandler

logger = logging.getLogger(__name__)

class AnalyticsHandler(BaseChannelHandler):
    """
    Analytics Handler responsible for message routing and transformations.
    Routes messages between service and processor layers.
    """
    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.module_identifier = ModuleIdentifier(
            component_name="analytics_handler",
            component_type=ComponentType.ANALYTICS_HANDLER,
            department="analytics",
            role="handler"
        )

        # Message routing configuration
        self.route_map = self._initialize_route_map()
        self._setup_message_handlers()

    def _initialize_route_map(self) -> Dict[MessageType, tuple]:
        """Initialize message routing configuration"""
        return {
            # Service → Processor routes
            MessageType.ANALYTICS_HANDLER_START: (
                ComponentType.ANALYTICS_PROCESSOR,
                MessageType.ANALYTICS_PROCESS_START
            ),
            MessageType.ANALYTICS_HANDLER_PAUSE: (
                ComponentType.ANALYTICS_PROCESSOR,
                MessageType.ANALYTICS_PROCESS_PAUSE
            ),
            MessageType.ANALYTICS_HANDLER_RESUME: (
                ComponentType.ANALYTICS_PROCESSOR,
                MessageType.ANALYTICS_PROCESS_RESUME
            ),
            MessageType.ANALYTICS_HANDLER_CANCEL: (
                ComponentType.ANALYTICS_PROCESSOR,
                MessageType.ANALYTICS_PROCESS_CANCEL
            ),

            # Processor → Service routes
            MessageType.ANALYTICS_PROCESS_COMPLETE: (
                ComponentType.ANALYTICS_SERVICE,
                MessageType.ANALYTICS_HANDLER_COMPLETE
            ),
            MessageType.ANALYTICS_PROCESS_ERROR: (
                ComponentType.ANALYTICS_SERVICE,
                MessageType.ANALYTICS_HANDLER_ERROR
            ),
            MessageType.ANALYTICS_PROCESS_STATUS: (
                ComponentType.ANALYTICS_SERVICE,
                MessageType.ANALYTICS_HANDLER_UPDATE
            ),

            # Stage completion routes
            MessageType.ANALYTICS_DATA_PREPARE_COMPLETE: (
                ComponentType.ANALYTICS_SERVICE,
                MessageType.ANALYTICS_HANDLER_UPDATE
            ),
            MessageType.ANALYTICS_FEATURE_ENGINEER_COMPLETE: (
                ComponentType.ANALYTICS_SERVICE,
                MessageType.ANALYTICS_HANDLER_UPDATE
            ),
            MessageType.ANALYTICS_MODEL_TRAIN_COMPLETE: (
                ComponentType.ANALYTICS_SERVICE,
                MessageType.ANALYTICS_HANDLER_UPDATE
            ),
            MessageType.ANALYTICS_MODEL_EVALUATE_COMPLETE: (
                ComponentType.ANALYTICS_SERVICE,
                MessageType.ANALYTICS_HANDLER_UPDATE
            )
        }

    def _setup_message_handlers(self) -> None:
        """Setup message handlers based on route map"""
        for source_type in self.route_map.keys():
            self.message_broker.subscribe(
                self.module_identifier,
                source_type.value,
                self._handle_message
            )

    async def _handle_message(self, message: ProcessingMessage) -> None:
        """Route message based on message type"""
        try:
            route = self.route_map.get(message.message_type)
            if not route:
                logger.warning(f"No route found for message type: {message.message_type}")
                return

            target_component, target_message_type = route
            await self._route_message(message, target_component, target_message_type)

        except Exception as e:
            logger.error(f"Message handling failed: {str(e)}")
            await self._handle_routing_error(message, str(e))

    async def _route_message(
        self,
        message: ProcessingMessage,
        target_component: ComponentType,
        target_message_type: MessageType
    ) -> None:
        """Route message to target component with transformation"""
        try:
            # Transform message for target
            transformed_content = self._transform_content(
                message.content,
                message.message_type,
                target_message_type
            )

            # Create routed message
            routed_message = ProcessingMessage(
                message_type=target_message_type,
                content=transformed_content,
                metadata=MessageMetadata(
                    correlation_id=message.metadata.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component=target_component.value,
                    domain_type="analytics",
                    processing_stage=message.metadata.processing_stage
                ),
                source_identifier=self.module_identifier
            )

            # Send to target
            await self.message_broker.publish(routed_message)

        except Exception as e:
            logger.error(f"Message routing failed: {str(e)}")
            await self._handle_routing_error(message, str(e))

    def _transform_content(
        self,
        content: Dict[str, Any],
        source_type: MessageType,
        target_type: MessageType
    ) -> Dict[str, Any]:
        """Transform message content based on source and target types"""
        transformations = {
            # Service → Processor transformations
            (MessageType.ANALYTICS_HANDLER_START, MessageType.ANALYTICS_PROCESS_START):
                self._transform_start_request,

            # Processor → Service transformations
            (MessageType.ANALYTICS_PROCESS_COMPLETE, MessageType.ANALYTICS_HANDLER_COMPLETE):
                self._transform_completion_result,

            # Status update transformations
            (MessageType.ANALYTICS_PROCESS_STATUS, MessageType.ANALYTICS_HANDLER_UPDATE):
                self._transform_status_update
        }

        transformer = transformations.get((source_type, target_type))
        if transformer:
            return transformer(content)
        return content  # Default: pass through unchanged

    def _transform_start_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Transform start request for processor"""
        return {
            "pipeline_id": content["pipeline_id"],
            "parameters": content.get("config", {}).get("parameters", {}),
            "data_config": content.get("config", {}).get("data_config", {}),
            "model_config": content.get("config", {}).get("model_config", {}),
            "context": content.get("context", {})
        }

    def _transform_completion_result(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Transform completion result for service"""
        return {
            "pipeline_id": content["pipeline_id"],
            "results": content.get("results", {}),
            "metrics": content.get("metrics", {}),
            "artifacts": content.get("artifacts", {}),
            "completion_time": datetime.now().isoformat()
        }

    def _transform_status_update(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Transform status update for service"""
        return {
            "pipeline_id": content["pipeline_id"],
            "stage": content.get("stage"),
            "progress": content.get("progress"),
            "metrics": content.get("metrics", {}),
            "timestamp": datetime.now().isoformat()
        }

    async def _handle_routing_error(
        self,
        original_message: ProcessingMessage,
        error: str
    ) -> None:
        """Handle message routing errors"""
        error_message = ProcessingMessage(
            message_type=MessageType.ANALYTICS_HANDLER_ERROR,
            content={
                "pipeline_id": original_message.content.get("pipeline_id"),
                "error": f"Message routing failed: {error}",
                "original_message_type": original_message.message_type.value,
                "timestamp": datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                correlation_id=original_message.metadata.correlation_id,
                source_component=self.module_identifier.component_name,
                target_component="analytics_service"
            ),
            source_identifier=self.module_identifier
        )

        await self.message_broker.publish(error_message)

    async def cleanup(self) -> None:
        """Clean up handler resources"""
        try:
            await self.message_broker.unsubscribe_all(self.module_identifier)
        except Exception as e:
            logger.error(f"Handler cleanup failed: {str(e)}")