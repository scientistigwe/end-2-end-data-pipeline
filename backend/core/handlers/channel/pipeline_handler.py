# backend/core/handlers/pipeline_handler.py

import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List, Callable, Coroutine

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    ComponentType,
    ModuleIdentifier
)
from ..base.base_handler import BaseChannelHandler
from ...managers.quality_manager import QualityManager
from ...managers.insight_manager import InsightManager
from ...managers.decision_manager import DecisionManager
from ...managers.recommendation_manager import RecommendationManager
from ...managers.report_manager import ReportManager

logger = logging.getLogger(__name__)


class PipelineHandler(BaseChannelHandler):
    """
    Dedicated handler for orchestrating pipeline workflows
    Coordinates processing across different domain-specific managers
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            quality_manager: QualityManager,
            insight_manager: InsightManager,
            decision_manager: DecisionManager,
            recommendation_manager: RecommendationManager,
            report_manager: ReportManager
    ):
        """
        Initialize pipeline handler with domain-specific managers

        Args:
            message_broker: Message communication system
            quality_manager: Quality analysis manager
            insight_manager: Insight generation manager
            decision_manager: Decision processing manager
            recommendation_manager: Recommendation generation manager
            report_manager: Report generation manager
        """
        super().__init__(message_broker, "pipeline_handler")

        # Domain-specific managers
        self.managers = {
            ProcessingStage.QUALITY_CHECK: quality_manager,
            ProcessingStage.INSIGHT_GENERATION: insight_manager,
            ProcessingStage.DECISION_MAKING: decision_manager,
            ProcessingStage.RECOMMENDATION: recommendation_manager,
            ProcessingStage.REPORT_GENERATION: report_manager
        }

        # Pipeline processing sequence
        self.pipeline_stages = [
            ProcessingStage.QUALITY_CHECK,
            ProcessingStage.INSIGHT_GENERATION,
            ProcessingStage.ADVANCED_ANALYTICS,
            ProcessingStage.DECISION_MAKING,
            ProcessingStage.RECOMMENDATION,
            ProcessingStage.REPORT_GENERATION
        ]

        # Active pipeline tracking
        self.active_pipelines: Dict[str, Dict[str, Any]] = {}

    async def initialize(self):
        """
        Initialize pipeline handler and setup message handlers
        """
        try:
            # Setup message handlers
            await self._setup_pipeline_handlers()
        except Exception as e:
            logger.error(f"Pipeline handler initialization error: {e}")
            raise

    async def _setup_pipeline_handlers(self):
        """
        Setup message handlers for pipeline-related events
        """
        handlers = {
            MessageType.PIPELINE_START: self._handle_pipeline_start,
            MessageType.PIPELINE_STAGE_START: self._handle_stage_start,
            MessageType.PIPELINE_STAGE_COMPLETE: self._handle_stage_complete,
            MessageType.PIPELINE_PAUSE: self._handle_pipeline_pause,
            MessageType.PIPELINE_RESUME: self._handle_pipeline_resume,
            MessageType.PIPELINE_CANCEL: self._handle_pipeline_cancel
        }

        for message_type, handler in handlers.items():
            await self.register_callback(message_type, handler)

    async def _handle_pipeline_start(self, message: ProcessingMessage):
        """
        Handle pipeline initialization and first stage processing

        Args:
            message: Pipeline start processing message
        """
        try:
            # Extract pipeline configuration
            pipeline_id = message.content.get('pipeline_id', str(uuid.uuid4()))
            initial_data = message.content.get('data', {})

            # Create pipeline tracking context
            pipeline_context = {
                'id': pipeline_id,
                'status': ProcessingStatus.RUNNING,
                'current_stage': self.pipeline_stages[0],
                'stages_completed': [],
                'data': initial_data,
                'errors': []
            }
            self.active_pipelines[pipeline_id] = pipeline_context

            # Trigger first stage processing
            await self._process_next_stage(pipeline_id)

        except Exception as e:
            await self._handle_pipeline_error(pipeline_id, e)

    async def _handle_stage_start(self, message: ProcessingMessage):
        """
        Handle specific stage initialization

        Args:
            message: Stage start processing message
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            stage = message.content.get('stage')

            if not pipeline_id or not stage:
                raise ValueError("Missing pipeline_id or stage")

            pipeline_context = self.active_pipelines.get(pipeline_id)
            if not pipeline_context:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            # Validate stage progression
            current_stage_index = self.pipeline_stages.index(pipeline_context['current_stage'])
            expected_stage_index = current_stage_index + 1

            if stage != self.pipeline_stages[expected_stage_index]:
                raise ValueError(f"Unexpected stage progression: {stage}")

            # Process stage
            await self._process_stage(pipeline_id, stage)

        except Exception as e:
            await self._handle_pipeline_error(pipeline_id, e)

    async def _process_stage(self, pipeline_id: str, stage: ProcessingStage):
        """
        Process a specific pipeline stage

        Args:
            pipeline_id: Unique pipeline identifier
            stage: Processing stage to execute
        """
        pipeline_context = self.active_pipelines[pipeline_id]
        manager = self.managers.get(stage)

        if not manager:
            raise ValueError(f"No manager configured for stage: {stage}")

        try:
            # Execute stage-specific processing
            stage_result = await manager.process_stage(
                pipeline_id=pipeline_id,
                data=pipeline_context['data']
            )

            # Update pipeline context
            pipeline_context['data'] = stage_result
            pipeline_context['stages_completed'].append(stage)
            pipeline_context['current_stage'] = stage

            # Notify stage completion
            await self._notify_stage_complete(pipeline_id, stage, stage_result)

        except Exception as e:
            await self._handle_stage_error(pipeline_id, stage, e)

    async def _process_next_stage(self, pipeline_id: str):
        """
        Progress to the next pipeline stage

        Args:
            pipeline_id: Unique pipeline identifier
        """
        pipeline_context = self.active_pipelines[pipeline_id]
        current_stage_index = self.pipeline_stages.index(pipeline_context['current_stage'])

        if current_stage_index + 1 < len(self.pipeline_stages):
            next_stage = self.pipeline_stages[current_stage_index + 1]
            await self._process_stage(pipeline_id, next_stage)
        else:
            # Pipeline complete
            await self._finalize_pipeline(pipeline_id)

    async def _finalize_pipeline(self, pipeline_id: str):
        """
        Complete pipeline processing

        Args:
            pipeline_id: Unique pipeline identifier
        """
        pipeline_context = self.active_pipelines[pipeline_id]
        pipeline_context['status'] = ProcessingStatus.COMPLETED

        # Publish pipeline completion event
        completion_message = ProcessingMessage(
            source_identifier=self.module_id,
            target_identifier=ModuleIdentifier(
                component_name="pipeline_manager",
                component_type=ComponentType.MANAGER,
                method_name="pipeline_complete"
            ),
            message_type=MessageType.PIPELINE_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'status': ProcessingStatus.COMPLETED.value,
                'data': pipeline_context['data']
            }
        )
        await self.message_broker.publish(completion_message)

        # Cleanup pipeline context
        del self.active_pipelines[pipeline_id]

    async def _handle_stage_complete(self, message: ProcessingMessage):
        """
        Handle stage completion and trigger next stage

        Args:
            message: Stage completion message
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            stage = message.content.get('stage')

            if not pipeline_id or not stage:
                raise ValueError("Missing pipeline_id or stage")

            # Progress to next stage
            await self._process_next_stage(pipeline_id)

        except Exception as e:
            await self._handle_pipeline_error(pipeline_id, e)

    async def _handle_pipeline_pause(self, message: ProcessingMessage):
        """
        Handle pipeline pause request

        Args:
            message: Pipeline pause message
        """
        pipeline_id = message.content.get('pipeline_id')

        if pipeline_id in self.active_pipelines:
            pipeline_context = self.active_pipelines[pipeline_id]
            pipeline_context['status'] = ProcessingStatus.PAUSED

            # Notify pause
            pause_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="pipeline_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="pipeline_pause"
                ),
                message_type=MessageType.PIPELINE_PAUSE,
                content={
                    'pipeline_id': pipeline_id,
                    'status': ProcessingStatus.PAUSED.value
                }
            )
            await self.message_broker.publish(pause_message)

    async def _handle_pipeline_resume(self, message: ProcessingMessage):
        """
        Handle pipeline resume request

        Args:
            message: Pipeline resume message
        """
        pipeline_id = message.content.get('pipeline_id')

        if pipeline_id in self.active_pipelines:
            pipeline_context = self.active_pipelines[pipeline_id]
            pipeline_context['status'] = ProcessingStatus.RUNNING

            # Resume from current stage
            await self._process_stage(pipeline_id, pipeline_context['current_stage'])

    async def _handle_pipeline_cancel(self, message: ProcessingMessage):
        """
        Handle pipeline cancellation request

        Args:
            message: Pipeline cancel message
        """
        pipeline_id = message.content.get('pipeline_id')

        if pipeline_id in self.active_pipelines:
            pipeline_context = self.active_pipelines[pipeline_id]
            pipeline_context['status'] = ProcessingStatus.CANCELLED

            # Notify cancellation
            cancel_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="pipeline_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="pipeline_cancel"
                ),
                message_type=MessageType.PIPELINE_CANCEL,
                content={
                    'pipeline_id': pipeline_id,
                    'status': ProcessingStatus.CANCELLED.value
                }
            )
            await self.message_broker.publish(cancel_message)

            # Cleanup pipeline context
            del self.active_pipelines[pipeline_id]

    async def _handle_stage_error(
            self,
            pipeline_id: str,
            stage: ProcessingStage,
            error: Exception
    ):
        """
        Handle errors during stage processing

        Args:
            pipeline_id: Unique pipeline identifier
            stage: Stage where error occurred
            error: Exception that occurred
        """
        pipeline_context = self.active_pipelines.get(pipeline_id)
        if pipeline_context:
            pipeline_context['status'] = ProcessingStatus.FAILED
            pipeline_context['errors'].append({
                'stage': stage.value,
                'error': str(error)
            })

        # Publish error message
        error_message = ProcessingMessage(
            source_identifier=self.module_id,
            target_identifier=ModuleIdentifier(
                component_name="pipeline_manager",
                component_type=ComponentType.MANAGER,
                method_name="pipeline_error"
            ),
            message_type=MessageType.PIPELINE_ERROR,
            content={
                'pipeline_id': pipeline_id,
                'stage': stage.value,
                'error': str(error),
                'status': ProcessingStatus.FAILED.value
            }
        )
        await self.message_broker.publish(error_message)

    async def _handle_pipeline_error(
            self,
            pipeline_id: str,
            error: Exception
    ):
        """
        Handle general pipeline errors

        Args:
            pipeline_id: Unique pipeline identifier
            error: Exception that occurred
        """
        if pipeline_id in self.active_pipelines:
            pipeline_context = self.active_pipelines[pipeline_id]
            pipeline_context['status'] = ProcessingStatus.FAILED
            pipeline_context['errors'].append({
                'error': str(error)
            })

        # Publish error message
        error_message = ProcessingMessage(
            source_identifier=self.module_id,
            target_identifier=ModuleIdentifier(
                component_name="pipeline_manager",
                component_type=ComponentType.MANAGER,
                method_name="pipeline_error"
            ),
            message_type=MessageType.PIPELINE_ERROR,
            content={
                'pipeline_id': pipeline_id,
                'error': str(error),
                'status': ProcessingStatus.FAILED.value
            }
        )
        await self.message_broker.publish(error_message)