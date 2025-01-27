# backend/core/services/analytics_service.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    AnalyticsContext,
    ModuleIdentifier,
    ComponentType,
    ProcessingStage,
    ProcessingStatus
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Analytics Service orchestrates business processes between manager and handler.
    Handles service-level operations and process control.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.module_identifier = ModuleIdentifier(
            component_name="analytics_service",
            component_type=ComponentType.ANALYTICS_SERVICE,
            department="analytics",
            role="service"
        )

        # Track active service requests
        self.active_requests: Dict[str, AnalyticsContext] = {}

        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Initialize message handlers"""
        handlers = {
            # Service Management
            MessageType.ANALYTICS_SERVICE_START: self._handle_service_start,
            MessageType.ANALYTICS_SERVICE_STOP: self._handle_service_stop,

            # Process Control
            MessageType.ANALYTICS_SERVICE_CONTROL: self._handle_service_control,
            MessageType.ANALYTICS_SERVICE_CONFIG: self._handle_service_config,

            # Status Management
            MessageType.ANALYTICS_SERVICE_STATUS: self._handle_service_status,
            MessageType.ANALYTICS_HANDLER_UPDATE: self._handle_handler_update,

            # Results and Completion
            MessageType.ANALYTICS_HANDLER_COMPLETE: self._handle_handler_complete,
            MessageType.ANALYTICS_HANDLER_ERROR: self._handle_handler_error
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_service_start(self, message: ProcessingMessage) -> None:
        """Handle service start request from manager"""
        try:
            pipeline_id = message.content["pipeline_id"]

            # Store context
            context = AnalyticsContext(**message.content["context"])
            self.active_requests[pipeline_id] = context

            # Forward to handler for processing
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_HANDLER_START,
                    content={
                        "pipeline_id": pipeline_id,
                        "config": message.content.get("config", {}),
                        "context": context.to_dict()
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="analytics_handler",
                        domain_type="analytics",
                        processing_stage=ProcessingStage.ADVANCED_ANALYTICS
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._handle_service_error(message, str(e))

    async def _handle_handler_update(self, message: ProcessingMessage) -> None:
        """Handle updates from handler"""
        pipeline_id = message.content["pipeline_id"]
        context = self.active_requests.get(pipeline_id)

        if not context:
            return

        # Update context
        context.update(message.content.get("updates", {}))

        # Forward to manager
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.ANALYTICS_STATUS_UPDATE,
                content={
                    "pipeline_id": pipeline_id,
                    "status": context.status,
                    "progress": message.content.get("progress"),
                    "current_stage": message.content.get("stage"),
                    "timestamp": datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="analytics_manager"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_handler_complete(self, message: ProcessingMessage) -> None:
        """Handle completion from handler"""
        pipeline_id = message.content["pipeline_id"]
        results = message.content.get("results", {})

        try:
            # Forward completion to manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_PROCESS_COMPLETE,
                    content={
                        "pipeline_id": pipeline_id,
                        "results": results,
                        "completion_time": datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="analytics_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup
            await self._cleanup_request(pipeline_id)

        except Exception as e:
            await self._handle_service_error(message, str(e))

    async def _handle_handler_error(self, message: ProcessingMessage) -> None:
        """Handle errors from handler"""
        pipeline_id = message.content["pipeline_id"]
        error = message.content.get("error", "Unknown error")

        try:
            # Forward error to manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_PROCESS_ERROR,
                    content={
                        "pipeline_id": pipeline_id,
                        "error": error,
                        "timestamp": datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="analytics_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup
            await self._cleanup_request(pipeline_id)

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    async def _handle_service_control(self, message: ProcessingMessage) -> None:
        """Handle service control commands"""
        pipeline_id = message.content["pipeline_id"]
        command = message.content.get("command")

        if command == "pause":
            await self._pause_processing(pipeline_id)
        elif command == "resume":
            await self._resume_processing(pipeline_id)
        elif command == "cancel":
            await self._cancel_processing(pipeline_id)

    async def _pause_processing(self, pipeline_id: str) -> None:
        """Pause processing for pipeline"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.ANALYTICS_HANDLER_PAUSE,
                content={"pipeline_id": pipeline_id},
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="analytics_handler"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _resume_processing(self, pipeline_id: str) -> None:
        """Resume processing for pipeline"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.ANALYTICS_HANDLER_RESUME,
                content={"pipeline_id": pipeline_id},
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="analytics_handler"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_service_error(self, message: ProcessingMessage, error: str) -> None:
        """Handle service-level errors"""
        pipeline_id = message.content.get("pipeline_id")

        if pipeline_id:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_SERVICE_ERROR,
                    content={
                        "pipeline_id": pipeline_id,
                        "error": error,
                        "timestamp": datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="analytics_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            await self._cleanup_request(pipeline_id)

    async def _cleanup_request(self, pipeline_id: str) -> None:
        """Clean up service request"""
        if pipeline_id in self.active_requests:
            del self.active_requests[pipeline_id]

    async def cleanup(self) -> None:
        """Clean up service resources"""
        try:
            # Cancel all active requests
            for pipeline_id in list(self.active_requests.keys()):
                await self._cancel_processing(pipeline_id)
                await self._cleanup_request(pipeline_id)

            # Unsubscribe from broker
            await self.message_broker.unsubscribe_all(self.module_identifier)

        except Exception as e:
            logger.error(f"Service cleanup failed: {str(e)}")