# backend/core/services/insight_service.py

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


class InsightService:
    """
    Insight Service: Orchestrates insight generation workflow between Manager and Handler.
    Handles business process coordination while maintaining message-driven architecture.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        # Service identification
        self.module_identifier = ModuleIdentifier(
            component_name="insight_service",
            component_type=ComponentType.INSIGHT_SERVICE,
            department="insight",
            role="service"
        )

        # Active request tracking
        self.active_requests: Dict[str, InsightContext] = {}

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup handlers for service messages"""
        handlers = {
            # Manager Messages
            MessageType.INSIGHT_SERVICE_START: self._handle_service_start,
            MessageType.INSIGHT_SERVICE_UPDATE: self._handle_service_update,
            MessageType.INSIGHT_SERVICE_DECISION: self._handle_service_decision,

            # Handler Responses
            MessageType.INSIGHT_HANDLER_COMPLETE: self._handle_handler_complete,
            MessageType.INSIGHT_HANDLER_ERROR: self._handle_handler_error,
            MessageType.INSIGHT_HANDLER_STATUS: self._handle_handler_status,

            # Status Messages
            MessageType.INSIGHT_VALIDATION_RESULT: self._handle_validation_result,
            MessageType.INSIGHT_REVIEW_COMPLETE: self._handle_review_complete
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                f"insight.{message_type.value}.#",
                handler
            )

    async def _handle_service_start(self, message: ProcessingMessage) -> None:
        """Handle service start request from manager"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            config = message.content.get('config', {})

            # Create insight context
            context = InsightContext(
                pipeline_id=pipeline_id,
                status=ProcessingStatus.INITIALIZING,
                state=InsightState.INITIALIZING,
                config=config
            )
            self.active_requests[pipeline_id] = context

            # Forward to handler
            await self._publish_handler_start(pipeline_id, config)

            # Update manager on initialization
            await self._publish_service_status(
                pipeline_id=pipeline_id,
                status="initialized",
                progress=0.0
            )

        except Exception as e:
            logger.error(f"Service start failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_service_update(self, message: ProcessingMessage) -> None:
        """Handle service update request from manager"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            update_type = message.content.get('update_type')
            update_data = message.content.get('update_data', {})

            context = self.active_requests.get(pipeline_id)
            if not context:
                raise ValueError(f"No active request for pipeline: {pipeline_id}")

            # Forward update to handler
            await self._publish_handler_update(
                pipeline_id=pipeline_id,
                update_type=update_type,
                update_data=update_data
            )

        except Exception as e:
            logger.error(f"Service update failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_handler_complete(self, message: ProcessingMessage) -> None:
        """Handle completion from insight handler"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            results = message.content.get('results', {})

            context = self.active_requests.get(pipeline_id)
            if context:
                context.state = InsightState.COMPLETION

                # Notify manager of completion
                await self._publish_service_complete(
                    pipeline_id=pipeline_id,
                    results=results
                )

                # Cleanup
                del self.active_requests[pipeline_id]

        except Exception as e:
            logger.error(f"Handler completion processing failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_handler_status(self, message: ProcessingMessage) -> None:
        """Handle status update from handler"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            status = message.content.get('status')
            progress = message.content.get('progress', 0.0)

            # Forward status to manager
            await self._publish_service_status(
                pipeline_id=pipeline_id,
                status=status,
                progress=progress
            )

        except Exception as e:
            logger.error(f"Handler status processing failed: {str(e)}")

    async def _publish_handler_start(self, pipeline_id: str, config: Dict[str, Any]) -> None:
        """Publish start request to handler"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.INSIGHT_HANDLER_START,
                content={
                    'pipeline_id': pipeline_id,
                    'config': config,
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="insight_handler",
                    domain_type="insight",
                    processing_stage=ProcessingStage.INSIGHT_GENERATION
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _publish_service_status(
            self,
            pipeline_id: str,
            status: str,
            progress: float
    ) -> None:
        """Publish status update to manager"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.INSIGHT_SERVICE_STATUS,
                content={
                    'pipeline_id': pipeline_id,
                    'status': status,
                    'progress': progress,
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="insight_manager",
                    domain_type="insight",
                    processing_stage=ProcessingStage.INSIGHT_GENERATION
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_error(
            self,
            original_message: ProcessingMessage,
            error: str
    ) -> None:
        """Handle and propagate errors"""
        try:
            pipeline_id = original_message.content.get('pipeline_id')

            # Update context if exists
            context = self.active_requests.get(pipeline_id)
            if context:
                context.state = InsightState.ERROR
                context.errors.append({
                    'error': error,
                    'timestamp': datetime.utcnow().isoformat()
                })

            # Notify manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_SERVICE_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'original_message': original_message.content,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="insight_manager",
                        domain_type="insight",
                        processing_stage=ProcessingStage.INSIGHT_GENERATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup on error
            if pipeline_id in self.active_requests:
                del self.active_requests[pipeline_id]

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup service resources"""
        try:
            # Notify cleanup for active requests
            for pipeline_id in list(self.active_requests.keys()):
                await self._handle_error(
                    ProcessingMessage(
                        message_type=MessageType.INSIGHT_SERVICE_ERROR,
                        content={'pipeline_id': pipeline_id}
                    ),
                    "Service cleanup initiated"
                )
                del self.active_requests[pipeline_id]

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise