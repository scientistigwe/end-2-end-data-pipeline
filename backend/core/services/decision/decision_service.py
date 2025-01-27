# backend/core/services/decision_service.py

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
    DecisionState,
    DecisionContext
)

logger = logging.getLogger(__name__)


class DecisionService:
    """
    Decision Service orchestrates the business process between manager and handler.
    Focuses on process orchestration and delegation.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.module_identifier = ModuleIdentifier(
            component_name="decision_service",
            component_type=ComponentType.DECISION_SERVICE,
            department="decision",
            role="service"
        )

        # Track active service requests
        self.active_requests: Dict[str, DecisionContext] = {}

        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Initialize all message handlers"""
        handlers = {
            # Manager Requests
            MessageType.DECISION_SERVICE_START: self._handle_service_start,
            MessageType.DECISION_SERVICE_VALIDATE: self._handle_service_validate,
            MessageType.DECISION_SERVICE_ANALYZE_IMPACT: self._handle_service_analyze_impact,

            # Handler Responses
            MessageType.DECISION_HANDLER_COMPLETE: self._handle_handler_complete,
            MessageType.DECISION_HANDLER_ERROR: self._handle_handler_error,
            MessageType.DECISION_HANDLER_UPDATE: self._handle_handler_update,

            # Process Control
            MessageType.DECISION_SERVICE_CONTROL: self._handle_service_control,
            MessageType.DECISION_SERVICE_CONFIG: self._handle_service_config,

            # Status Management
            MessageType.DECISION_SERVICE_STATUS: self._handle_service_status,

            # Resource Management
            MessageType.DECISION_RESOURCE_ACQUIRED: self._handle_resource_acquired,
            MessageType.DECISION_RESOURCE_RELEASED: self._handle_resource_released
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

            # Create and store context
            context = DecisionContext(
                pipeline_id=pipeline_id,
                correlation_id=message.metadata.correlation_id,
                config=message.content.get("config", {}),
                options=message.content.get("options", [])
            )
            self.active_requests[pipeline_id] = context

            # Forward to handler for processing
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_HANDLER_START,
                    content={
                        "pipeline_id": pipeline_id,
                        "context": context.to_dict(),
                        "config": context.config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="decision_handler",
                        domain_type="decision",
                        processing_stage=ProcessingStage.DECISION_MAKING
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Service start failed: {str(e)}")
            await self._handle_service_error(message, str(e))

    async def _handle_service_validate(self, message: ProcessingMessage) -> None:
        """Handle validation request from manager"""
        try:
            pipeline_id = message.content["pipeline_id"]
            context = self.active_requests.get(pipeline_id)

            if not context:
                raise ValueError(f"No active context for pipeline {pipeline_id}")

            # Forward validation request to handler
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_HANDLER_VALIDATE,
                    content={
                        "pipeline_id": pipeline_id,
                        "options": message.content.get("options", []),
                        "constraints": message.content.get("constraints", {})
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="decision_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Validation request failed: {str(e)}")
            await self._handle_service_error(message, str(e))

    async def _handle_service_analyze_impact(self, message: ProcessingMessage) -> None:
        """Handle impact analysis request from manager"""
        try:
            pipeline_id = message.content["pipeline_id"]
            context = self.active_requests.get(pipeline_id)

            if not context:
                raise ValueError(f"No active context for pipeline {pipeline_id}")

            # Forward impact analysis request to handler
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_HANDLER_ANALYZE_IMPACT,
                    content={
                        "pipeline_id": pipeline_id,
                        "options": message.content.get("options", []),
                        "config": message.content.get("config", {})
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="decision_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Impact analysis request failed: {str(e)}")
            await self._handle_service_error(message, str(e))

    async def _handle_handler_complete(self, message: ProcessingMessage) -> None:
        """Handle completion message from handler"""
        try:
            pipeline_id = message.content["pipeline_id"]
            context = self.active_requests.get(pipeline_id)

            if not context:
                return

            # Forward completion to manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_SERVICE_COMPLETE,
                    content={
                        "pipeline_id": pipeline_id,
                        "results": message.content.get("results", {}),
                        "completion_time": datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="decision_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup request
            await self._cleanup_request(pipeline_id)

        except Exception as e:
            logger.error(f"Handler completion processing failed: {str(e)}")
            await self._handle_service_error(message, str(e))

    async def _handle_handler_update(self, message: ProcessingMessage) -> None:
        """Handle status update from handler"""
        try:
            pipeline_id = message.content["pipeline_id"]
            context = self.active_requests.get(pipeline_id)

            if not context:
                return

            # Update context with handler progress
            context.state = message.content.get("state", context.state)
            context.progress = message.content.get("progress", context.progress)

            # Forward status to manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_SERVICE_STATUS,
                    content={
                        "pipeline_id": pipeline_id,
                        "state": context.state,
                        "progress": context.progress,
                        "timestamp": datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="decision_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Handler update processing failed: {str(e)}")
            await self._handle_service_error(message, str(e))

    async def _handle_handler_error(self, message: ProcessingMessage) -> None:
        """Handle error message from handler"""
        try:
            pipeline_id = message.content["pipeline_id"]
            error = message.content.get("error", "Unknown error")

            # Forward error to manager
            await self._handle_service_error(message, error)

            # Cleanup request
            await self._cleanup_request(pipeline_id)

        except Exception as e:
            logger.error(f"Handler error processing failed: {str(e)}")

    async def _handle_service_control(self, message: ProcessingMessage) -> None:
        """Handle service control commands"""
        try:
            pipeline_id = message.content["pipeline_id"]
            command = message.content.get("command")

            if command == "pause":
                await self._pause_processing(pipeline_id)
            elif command == "resume":
                await self._resume_processing(pipeline_id)
            elif command == "cancel":
                await self._cancel_processing(pipeline_id)

        except Exception as e:
            logger.error(f"Service control failed: {str(e)}")
            await self._handle_service_error(message, str(e))

    async def _pause_processing(self, pipeline_id: str) -> None:
        """Pause processing for pipeline"""
        context = self.active_requests.get(pipeline_id)
        if not context:
            return

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.DECISION_HANDLER_PAUSE,
                content={"pipeline_id": pipeline_id},
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="decision_handler"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _resume_processing(self, pipeline_id: str) -> None:
        """Resume processing for pipeline"""
        context = self.active_requests.get(pipeline_id)
        if not context:
            return

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.DECISION_HANDLER_RESUME,
                content={"pipeline_id": pipeline_id},
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="decision_handler"
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
                    message_type=MessageType.DECISION_SERVICE_ERROR,
                    content={
                        "pipeline_id": pipeline_id,
                        "error": error,
                        "timestamp": datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="decision_manager"
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