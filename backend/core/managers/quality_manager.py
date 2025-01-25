# backend/core/sub_managers/quality_manager.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    ProcessingStage,
    MessageMetadata,
    QualityContext
)
from ..managers.base.base_manager import BaseManager, ManagerState
from data.processing.quality.types.quality_types import QualityState, QualityMetrics

logger = logging.getLogger(__name__)


class QualityManager(BaseManager):
    """
    Quality Manager that coordinates quality analysis through message broker.
    Maintains local state but communicates all actions through messages.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(
            message_broker=message_broker,
            component_name="quality_manager",
            domain_type="quality"
        )

        # Local state tracking
        self.active_processes: Dict[str, QualityContext] = {}

        # Register message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Register handlers for all quality-related messages"""
        handlers = {
            MessageType.QUALITY_START_REQUEST: self._handle_start_request,
            MessageType.QUALITY_STATE_UPDATE: self._handle_state_update,
            MessageType.QUALITY_RESULTS_READY: self._handle_results_ready,
            MessageType.QUALITY_ISSUE_DETECTED: self._handle_issue_detected,
            MessageType.QUALITY_VALIDATION_RESULT: self._handle_validation_result,
            MessageType.QUALITY_RESOLUTION_RESULT: self._handle_resolution_result,
            MessageType.QUALITY_PROCESS_COMPLETE: self._handle_process_complete,
            MessageType.QUALITY_ERROR: self._handle_error,
            MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
            MessageType.CONTROL_POINT_UPDATED: self._handle_control_point_updated,
            MessageType.STAGING_AREA_CREATED: self._handle_staging_created,
            MessageType.STAGING_DATA_READY: self._handle_staging_data_ready
        }

        for message_type, handler in handlers.items():
            self.register_message_handler(message_type, handler)

    async def initiate_quality_process(
            self,
            pipeline_id: str,
            config: Dict[str, Any]
    ) -> str:
        """
        Initiate quality analysis process through message broker
        Returns correlation ID for tracking
        """
        correlation_id = str(uuid.uuid4())

        # Request control point creation
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.CONTROL_POINT_CREATE_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.QUALITY_CHECK,
                'config': config
            },
            metadata=MessageMetadata(
                correlation_id=correlation_id,
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        ))

        # Initialize local tracking
        self.active_processes[pipeline_id] = QualityContext(
            pipeline_id=pipeline_id,
            correlation_id=correlation_id,
            state=QualityState.INITIALIZING,
            config=config,
            metrics=QualityMetrics()
        )

        return correlation_id

    async def _handle_control_point_created(self, message: ProcessingMessage) -> None:
        """Handle control point creation confirmation"""
        pipeline_id = message.content['pipeline_id']
        control_point_id = message.content['control_point_id']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.control_point_id = control_point_id

        # Request staging area creation
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGING_CREATE_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'control_point_id': control_point_id,
                'source_type': 'quality'
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="staging_manager"
            )
        ))

    async def _handle_staging_created(self, message: ProcessingMessage) -> None:
        """Handle staging area creation confirmation"""
        pipeline_id = message.content['pipeline_id']
        staged_id = message.content['staged_id']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.staged_id = staged_id

        # Start quality processing
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.QUALITY_START_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'staged_id': staged_id,
                'config': context.config
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="quality_handler"
            )
        ))

    async def _handle_issue_detected(self, message: ProcessingMessage) -> None:
        """Handle detected quality issues"""
        pipeline_id = message.content['pipeline_id']
        issues = message.content['issues']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.state = QualityState.ISSUE_DETECTED
        context.issues.extend(issues)

        # Notify about issues requiring attention
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.QUALITY_ISSUES_FOUND,
            content={
                'pipeline_id': pipeline_id,
                'issues': issues,
                'requires_attention': True
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        ))

    async def _handle_results_ready(self, message: ProcessingMessage) -> None:
        """Handle quality results availability"""
        pipeline_id = message.content['pipeline_id']
        results = message.content['results']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.results = results
        context.state = QualityState.COMPLETED

        # Notify process completion
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGE_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.QUALITY_CHECK,
                'results': results
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        ))

    async def _handle_error(self, message: ProcessingMessage) -> None:
        """Handle quality process errors"""
        pipeline_id = message.content['pipeline_id']
        error = message.content['error']

        context = self.active_processes.get(pipeline_id)
        if context:
            context.state = QualityState.FAILED
            context.error = error

            # Notify error
            await self.message_broker.publish(ProcessingMessage(
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.QUALITY_CHECK,
                    'error': error
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.component_name,
                    target_component="control_point_manager"
                )
            ))

            # Cleanup
            del self.active_processes[pipeline_id]

    async def cleanup(self) -> None:
        """Clean up manager resources"""
        try:
            # Notify cleanup for all active processes
            for pipeline_id in list(self.active_processes.keys()):
                await self.message_broker.publish(ProcessingMessage(
                    message_type=MessageType.QUALITY_CLEANUP,
                    content={
                        'pipeline_id': pipeline_id,
                        'reason': 'Manager cleanup initiated'
                    }
                ))
                del self.active_processes[pipeline_id]

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise