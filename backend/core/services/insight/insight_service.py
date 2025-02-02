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
            MessageType.INSIGHT_GENERATE_START: self._handle_service_start,
            MessageType.INSIGHT_GENERATE_UPDATE: self._handle_service_update,
            MessageType.INSIGHT_SERVICE_DECISION: self._handle_service_decision,

            # Handler Responses
            MessageType.INSIGHT_GENERATE_COMPLETE: self._handle_handler_complete,
            MessageType.INSIGHT_GENERATE_FAILED: self._handle_handler_error,
            MessageType.INSIGHT_GENERATE_PROGRESS: self._handle_handler_status,

            # Status Messages
            MessageType.INSIGHT_VALIDATE_COMPLETE: self._handle_validate_complete,
            MessageType.INSIGHT_REVIEW_COMPLETE: self._handle_review_complete
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                f"insight.{message_type.value}.#",
                handler
            )

    async def _handle_service_decision(self, message: ProcessingMessage) -> None:
        """Handle decision points from manager"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            decision = message.content.get('decision', {})
            context = self.active_requests.get(pipeline_id)

            if not context:
                raise ValueError(f"No active request for pipeline: {pipeline_id}")

            # Forward decision to handler
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_HANDLER_DECISION,
                    content={
                        'pipeline_id': pipeline_id,
                        'decision': decision,
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

        except Exception as e:
            logger.error(f"Service decision handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_validate_complete(self, message: ProcessingMessage) -> None:
        """Handle validation results from handler"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            validation_results = message.content.get('validation_results', {})
            context = self.active_requests.get(pipeline_id)

            if not context:
                return

            # Forward validation results to manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_VALIDATE_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'validation_results': validation_results,
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

        except Exception as e:
            logger.error(f"Validation result handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_review_complete(self, message: ProcessingMessage) -> None:
        """Handle completion of insight review"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            review_results = message.content.get('review_results', {})
            context = self.active_requests.get(pipeline_id)

            if not context:
                return

            if review_results.get('approved', False):
                # Forward completion to handler
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.INSIGHT_GENERATE_COMPLETE,
                        content={
                            'pipeline_id': pipeline_id,
                            'review_results': review_results,
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
            else:
                # Handle rejection
                await self._handle_review_rejection(pipeline_id, review_results)

        except Exception as e:
            logger.error(f"Review completion handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_review_rejection(self, pipeline_id: str, review_results: Dict[str, Any]) -> None:
        """Handle rejection of insights during review"""
        try:
            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Update context state
            context.state = InsightState.DETECTION_PREPARATION

            # Notify handler of rejection
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_VALIDATE_REJECT,
                    content={
                        'pipeline_id': pipeline_id,
                        'rejection_reason': review_results.get('reason', ''),
                        'feedback': review_results.get('feedback', {}),
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

        except Exception as e:
            logger.error(f"Review rejection handling failed: {str(e)}")
            await self._handle_error(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_SERVICE_ERROR,
                    content={'pipeline_id': pipeline_id}
                ),
                str(e)
            )

    async def _handle_handler_error(self, message: ProcessingMessage) -> None:
        """Handle errors reported by the handler"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            error = message.content.get('error', 'Unknown handler error')

            # Forward error to manager with additional context
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_GENERATE_FAILED,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'source': 'handler',
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

            # Clean up request
            if pipeline_id in self.active_requests:
                del self.active_requests[pipeline_id]

        except Exception as e:
            logger.error(f"Handler error processing failed: {str(e)}")

    async def _publish_handler_update(
            self,
            pipeline_id: str,
            update_type: str,
            update_data: Dict[str, Any]
    ) -> None:
        """Publish update request to handler"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.INSIGHT_HANDLER_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'update_type': update_type,
                    'update_data': update_data,
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

    async def _publish_service_complete(self, pipeline_id: str, results: Dict[str, Any]) -> None:
        """Publish completion notification to manager"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.INSIGHT_GENERATE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'results': results,
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