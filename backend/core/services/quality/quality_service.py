# backend/core/services/quality_service.py

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
    QualityState,
    QualityContext
)

logger = logging.getLogger(__name__)


class QualityService:
    """
    Quality Service orchestrates the business process between manager and handler.
    Acts as an intermediary for quality-related requests and processing.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.module_identifier = ModuleIdentifier(
            component_name="quality_service",
            component_type=ComponentType.QUALITY_SERVICE,
            department="quality",
            role="service"
        )

        # Track active service requests
        self.active_requests: Dict[str, QualityContext] = {}

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Initialize all message handlers"""
        handlers = {
            # Manager Requests
            MessageType.QUALITY_PROCESS_START: self._handle_process_start,
            MessageType.QUALITY_ANALYSE_REQUEST: self._handle_analyse_request,
            MessageType.QUALITY_VALIDATE_REQUEST: self._handle_validate_request,
            MessageType.QUALITY_RESOLUTION_REQUEST: self._handle_resolution_request,

            # Handler Responses
            MessageType.QUALITY_DETECTION_COMPLETE: self._handle_detection_complete,
            MessageType.QUALITY_ANALYSE_COMPLETE: self._handle_analyse_complete,
            MessageType.QUALITY_RESOLUTION_COMPLETE: self._handle_resolution_complete,
            MessageType.QUALITY_VALIDATE_COMPLETE: self._handle_validate_complete,

            # Status and Progress
            MessageType.QUALITY_PROCESS_STATUS: self._handle_process_status,
            MessageType.QUALITY_PROCESS_PROGRESS: self._handle_process_progress,
            MessageType.QUALITY_ISSUE_DETECTED: self._handle_issue_detected,

            # Error Handling
            MessageType.QUALITY_PROCESS_FAILED: self._handle_error
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_process_progress(self, message: ProcessingMessage) -> None:
        """Handle progress updates from handler"""
        try:
            pipeline_id = message.content["pipeline_id"]
            context = self.active_requests.get(pipeline_id)

            if not context:
                return

            # Update progress in context
            stage = message.content.get('stage', 'unknown')
            progress = message.content.get('progress', 0)
            context.processing_metrics[stage] = progress
            context.updated_at = datetime.now()

            # Forward progress to manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_PROCESS_PROGRESS,
                    content={
                        'pipeline_id': pipeline_id,
                        'stage': stage,
                        'progress': progress,
                        'state': context.state.value,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="quality_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Progress handling failed: {str(e)}")

    async def _handle_resolution_request(self, message: ProcessingMessage) -> None:
        """Handle resolution request from manager"""
        try:
            pipeline_id = message.content["pipeline_id"]
            context = self.active_requests.get(pipeline_id)

            if not context:
                raise ValueError(f"No active context for pipeline {pipeline_id}")

            # Forward resolution request to handler
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_RESOLUTION_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'issues': message.content.get('issues', []),
                        'resolution_config': message.content.get('config', {})
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="quality_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Resolution request failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_resolution_complete(self, message: ProcessingMessage) -> None:
        """Handle resolution completion from handler"""
        try:
            pipeline_id = message.content["pipeline_id"]
            context = self.active_requests.get(pipeline_id)

            if not context:
                return

            # Store resolution results
            context.applied_resolutions = message.content.get('resolutions', {})
            context.state = QualityState.VALIDATION

            # Forward to validation after resolution
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_VALIDATE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'resolutions': context.applied_resolutions,
                        'config': context.config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="quality_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Resolution completion handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _notify_status_update(self, pipeline_id: str, status: str) -> None:
        """Notify about status updates"""
        context = self.active_requests.get(pipeline_id)
        if not context:
            return

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.QUALITY_PROCESS_STATUS,
                content={
                    'pipeline_id': pipeline_id,
                    'status': status,
                    'state': context.state.value,
                    'progress': context.progress,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="quality_manager"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_process_start(self, message: ProcessingMessage) -> None:
        """Handle quality process start request from manager"""
        try:
            pipeline_id = message.content["pipeline_id"]

            # Create and store context
            context = QualityContext(
                pipeline_id=pipeline_id,
                correlation_id=message.metadata.correlation_id,
                state=QualityState.INITIALIZING,
                config=message.content.get("config", {})
            )
            self.active_requests[pipeline_id] = context

            # Forward to handler for processing
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_DETECTION_REQUEST,
                    content={
                        "pipeline_id": pipeline_id,
                        "context": context.to_dict(),
                        "config": context.config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="quality_handler",
                        domain_type="quality",
                        processing_stage=ProcessingStage.QUALITY_CHECK
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Process start failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_detection_complete(self, message: ProcessingMessage) -> None:
        """Handle detection completion from handler"""
        try:
            pipeline_id = message.content["pipeline_id"]
            context = self.active_requests.get(pipeline_id)

            if not context:
                return

            # Update context with detection results
            context.detected_issues = message.content.get("detected_issues", {})
            context.state = QualityState.ANALYSIS

            # Forward to analyze
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_ANALYSE_REQUEST,
                    content={
                        "pipeline_id": pipeline_id,
                        "detected_issues": context.detected_issues,
                        "config": context.config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="quality_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Detection completion handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_analyse_request(self, message: ProcessingMessage) -> None:
        """Handle analysis request from manager"""
        try:
            pipeline_id = message.content["pipeline_id"]
            context = self.active_requests.get(pipeline_id)

            if not context:
                raise ValueError(f"No active context for pipeline {pipeline_id}")

            # Forward analysis request to handler
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_ANALYSE_REQUEST,
                    content={
                        "pipeline_id": pipeline_id,
                        "config": message.content.get("config", {})
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="quality_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Analysis request failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_analyse_complete(self, message: ProcessingMessage) -> None:
        """Handle analysis completion from handler"""
        try:
            pipeline_id = message.content["pipeline_id"]
            context = self.active_requests.get(pipeline_id)

            if not context:
                return

            # Store analysis results
            context.analysis_results = message.content.get("results", {})
            context.state = QualityState.VALIDATION

            # Forward to validation
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_VALIDATE_REQUEST,
                    content={
                        "pipeline_id": pipeline_id,
                        "analysis_results": context.analysis_results,
                        "config": context.config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="quality_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Analysis completion handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_validate_request(self, message: ProcessingMessage) -> None:
        """Handle validation request"""
        try:
            pipeline_id = message.content["pipeline_id"]
            context = self.active_requests.get(pipeline_id)

            if not context:
                raise ValueError(f"No active context for pipeline {pipeline_id}")

            # Forward validation request to handler
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_VALIDATE_REQUEST,
                    content={
                        "pipeline_id": pipeline_id,
                        "config": message.content.get("config", {})
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="quality_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Validation request failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_validate_complete(self, message: ProcessingMessage) -> None:
        """Handle validation completion"""
        try:
            pipeline_id = message.content["pipeline_id"]
            context = self.active_requests.get(pipeline_id)

            if not context:
                return

            # Store validation results
            context.validation_results = message.content.get("validation_results", {})
            context.state = QualityState.COMPLETED

            # Notify manager of completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_PROCESS_COMPLETE,
                    content={
                        "pipeline_id": pipeline_id,
                        "results": {
                            "detected_issues": context.detected_issues,
                            "analysis_results": context.analysis_results,
                            "validation_results": context.validation_results
                        },
                        "completion_time": datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="quality_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup request
            await self._cleanup_request(pipeline_id)

        except Exception as e:
            logger.error(f"Validation completion failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_issue_detected(self, message: ProcessingMessage) -> None:
        """Handle detected quality issues"""
        try:
            pipeline_id = message.content["pipeline_id"]
            context = self.active_requests.get(pipeline_id)

            if not context:
                return

            # Forward issue detection to manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_ISSUE_DETECTED,
                    content={
                        "pipeline_id": pipeline_id,
                        "issues": message.content.get("issues", [])
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="quality_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Issue detection handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_process_status(self, message: ProcessingMessage) -> None:
        """Handle status request"""
        try:
            pipeline_id = message.content["pipeline_id"]
            context = self.active_requests.get(pipeline_id)

            if not context:
                return

            # Send status response
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_PROCESS_STATUS,
                    content={
                        "pipeline_id": pipeline_id,
                        "state": context.state.value,
                        "detected_issues_count": len(context.detected_issues),
                        "processing_metrics": context.processing_metrics
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component=message.metadata.source_component
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Status handling failed: {str(e)}")

    async def _handle_error(self, message: ProcessingMessage, error: str) -> None:
        """Handle service errors"""
        pipeline_id = message.content.get("pipeline_id")

        if pipeline_id:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_ERROR,
                    content={
                        "pipeline_id": pipeline_id,
                        "error": error,
                        "timestamp": datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="quality_manager"
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
            # Clean up all active requests
            for pipeline_id in list(self.active_requests.keys()):
                await self._cleanup_request(pipeline_id)

        except Exception as e:
            logger.error(f"Service cleanup failed: {str(e)}")