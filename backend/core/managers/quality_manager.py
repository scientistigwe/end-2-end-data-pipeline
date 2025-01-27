import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    QualityContext,
    QualityState,
    QualityMetrics,
    ComponentType,
    ModuleIdentifier
)
from .base.base_manager import BaseManager

logger = logging.getLogger(__name__)


class QualityManager(BaseManager):
    """
    Quality Manager that coordinates quality workflow.
    Subscribes to CPM messages and coordinates through service layer.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        self.module_identifier = ModuleIdentifier(
            component_name="quality_manager",
            component_type=ComponentType.QUALITY_MANAGER,
            department="quality",
            role="manager"
        )

        # Active quality processes
        self.active_processes: Dict[str, QualityContext] = {}

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup handlers for CPM messages"""
        handlers = {
            # CPM Messages
            MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
            MessageType.CONTROL_POINT_UPDATED: self._handle_control_point_updated,
            MessageType.CONTROL_POINT_DECISION: self._handle_control_point_decision,

            # Service Layer Responses
            MessageType.QUALITY_SERVICE_COMPLETE: self._handle_service_complete,
            MessageType.QUALITY_SERVICE_ERROR: self._handle_service_error,
            MessageType.QUALITY_SERVICE_STATUS: self._handle_service_status,

            # Quality Processing States
            MessageType.QUALITY_ISSUES_DETECTED: self._handle_issues_detected,
            MessageType.QUALITY_VALIDATION_COMPLETE: self._handle_validation_complete,
            MessageType.QUALITY_RESOLUTION_COMPLETE: self._handle_resolution_complete
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                f"{message_type.value}",
                handler
            )

    async def _handle_control_point_created(self, message: ProcessingMessage) -> None:
        """Handle new control point for quality check"""
        try:
            pipeline_id = message.content['pipeline_id']
            config = message.content.get('config', {})

            # Create quality context
            context = QualityContext(
                pipeline_id=pipeline_id,
                correlation_id=str(uuid.uuid4()),
                state=QualityState.INITIALIZING,
                metrics=QualityMetrics()
            )

            self.active_processes[pipeline_id] = context

            # Forward to service layer
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_SERVICE_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="quality_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to handle control point creation: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_issues_detected(self, message: ProcessingMessage) -> None:
        """Handle detected quality issues"""
        pipeline_id = message.content['pipeline_id']
        issues = message.content['issues']
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        # Update context
        context.add_issues(issues)

        # Notify CPM if manual intervention needed
        if context.requires_manual_intervention():
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.CONTROL_POINT_DECISION_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'type': 'quality_review',
                        'issues': issues
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="control_point_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

    async def _handle_control_point_decision(self, message: ProcessingMessage) -> None:
        """Handle quality review decision from CPM"""
        pipeline_id = message.content['pipeline_id']
        decision = message.content['decision']
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        # Forward decision to service
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.QUALITY_SERVICE_DECISION,
                content={
                    'pipeline_id': pipeline_id,
                    'decision': decision
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="quality_service"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_service_complete(self, message: ProcessingMessage) -> None:
        """Handle quality service completion"""
        pipeline_id = message.content['pipeline_id']
        results = message.content.get('results', {})
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        # Notify CPM of completion
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.STAGE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.QUALITY_CHECK,
                    'results': results
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager"
                ),
                source_identifier=self.module_identifier
            )
        )

        # Cleanup
        await self._cleanup_process(pipeline_id)

    async def _handle_service_error(self, message: ProcessingMessage) -> None:
        """Handle quality service errors"""
        pipeline_id = message.content['pipeline_id']
        error = message.content['error']
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        # Notify CPM of error
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.QUALITY_CHECK,
                    'error': error
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager"
                ),
                source_identifier=self.module_identifier
            )
        )

        # Cleanup
        await self._cleanup_process(pipeline_id)

    async def _handle_error(self, pipeline_id: str, error: str) -> None:
        """Handle manager-level errors"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        # Notify CPM
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.QUALITY_CHECK,
                    'error': error
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager"
                ),
                source_identifier=self.module_identifier
            )
        )

        # Cleanup
        await self._cleanup_process(pipeline_id)

    async def _cleanup_process(self, pipeline_id: str) -> None:
        """Cleanup quality process"""
        if pipeline_id in self.active_processes:
            del self.active_processes[pipeline_id]

    async def cleanup(self) -> None:
        """Cleanup manager resources"""
        try:
            # Cleanup all active processes
            for pipeline_id in list(self.active_processes.keys()):
                await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise