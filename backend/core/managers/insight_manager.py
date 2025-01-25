# backend/core/sub_managers/insight_manager.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    InsightContext,
    InsightState
)
from ..managers.base.base_manager import BaseManager

logger = logging.getLogger(__name__)


class InsightManager(BaseManager):
    """
    Insight Manager that coordinates insight generation through message broker.
    Maintains local state but communicates all actions through messages.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(
            message_broker=message_broker,
            component_name="insight_manager",
            domain_type="insights"
        )

        # Local state tracking
        self.active_processes: Dict[str, InsightContext] = {}

        # Register message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Register handlers for all insight-related messages"""
        handlers = {
            MessageType.INSIGHT_START_REQUEST: self._handle_start_request,
            MessageType.INSIGHT_STATE_UPDATE: self._handle_state_update,
            MessageType.INSIGHT_RESULTS_READY: self._handle_results_ready,
            MessageType.INSIGHT_VALIDATION_RESULT: self._handle_validation_result,
            MessageType.INSIGHT_REVIEW_REQUIRED: self._handle_review_required,
            MessageType.INSIGHT_REVIEW_COMPLETE: self._handle_review_complete,
            MessageType.INSIGHT_PROCESS_COMPLETE: self._handle_process_complete,
            MessageType.INSIGHT_ERROR: self._handle_insight_error,
            MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
            MessageType.STAGING_CREATED: self._handle_staging_created
        }

        for message_type, handler in handlers.items():
            self.register_message_handler(message_type, handler)

    async def initiate_insight_process(
            self,
            pipeline_id: str,
            config: Dict[str, Any]
    ) -> str:
        """
        Initiate insight generation through message broker
        Returns correlation ID for tracking
        """
        correlation_id = str(uuid.uuid4())

        # Request control point creation
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.CONTROL_POINT_CREATE_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.INSIGHT_GENERATION,
                'config': config
            },
            metadata=MessageMetadata(
                correlation_id=correlation_id,
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        ))

        # Initialize context
        self.active_processes[pipeline_id] = InsightContext(
            pipeline_id=pipeline_id,
            stage=ProcessingStage.INSIGHT_GENERATION,
            status=ProcessingStatus.PENDING,
            correlation_id=correlation_id,
            analysis_type=config.get('analysis_type', 'general_analysis'),
            target_metrics=config.get('target_metrics', []),
            confidence_threshold=config.get('confidence_threshold', 0.5)
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
                'source_type': 'insights'
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

        # Start insight processing
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.INSIGHT_START,
            content={
                'pipeline_id': pipeline_id,
                'staged_id': staged_id,
                'config': {
                    'analysis_type': context.analysis_type,
                    'target_metrics': context.target_metrics,
                    'confidence_threshold': context.confidence_threshold
                }
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="insight_handler"
            )
        ))

    async def _handle_results_ready(self, message: ProcessingMessage) -> None:
        """Handle insight results availability"""
        pipeline_id = message.content['pipeline_id']
        insights = message.content['insights']
        requires_review = message.content.get('requires_review', False)

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.insights = insights
        context.requires_review = requires_review
        context.state = (
            InsightState.AWAITING_REVIEW if requires_review
            else InsightState.COMPLETED
        )

        if requires_review:
            await self._request_insight_review(pipeline_id, insights)
        else:
            await self._complete_insight_process(pipeline_id, insights)

    async def _handle_review_required(self, message: ProcessingMessage) -> None:
        """Handle insights requiring review"""
        pipeline_id = message.content['pipeline_id']
        insights = message.content['insights']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.state = InsightState.AWAITING_REVIEW

        # Notify about required review
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGE_AWAITING_DECISION,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.INSIGHT_GENERATION,
                'insights': insights,
                'requires_review': True
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        ))

    async def _handle_review_complete(self, message: ProcessingMessage) -> None:
        """Handle completion of insight review"""
        pipeline_id = message.content['pipeline_id']
        reviewed_insights = message.content['insights']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        await self._complete_insight_process(pipeline_id, reviewed_insights)

    async def _complete_insight_process(
            self,
            pipeline_id: str,
            insights: List[Dict[str, Any]]
    ) -> None:
        """Handle completion of insight process"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.state = InsightState.COMPLETED
        context.insights = insights
        context.completed_at = datetime.now()

        # Notify completion
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGE_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.INSIGHT_GENERATION,
                'insights': insights
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        ))

        # Cleanup
        del self.active_processes[pipeline_id]

    async def _handle_insight_error(self, message: ProcessingMessage) -> None:
        """Handle insight processing errors"""
        pipeline_id = message.content['pipeline_id']
        error = message.content['error']

        context = self.active_processes.get(pipeline_id)
        if context:
            context.state = InsightState.FAILED
            context.error = error

            # Notify error
            await self.message_broker.publish(ProcessingMessage(
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.INSIGHT_GENERATION,
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
                    message_type=MessageType.INSIGHT_CLEANUP,
                    content={
                        'pipeline_id': pipeline_id,
                        'reason': 'Manager cleanup initiated'
                    }
                ))
                del self.active_processes[pipeline_id]

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise