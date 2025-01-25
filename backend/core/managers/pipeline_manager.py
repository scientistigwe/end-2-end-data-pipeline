# pipeline_manager.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import asyncio

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    PipelineContext,
    PipelineState,
    ModuleIdentifier,
    ComponentType
)
from ..monitoring.collectors import MetricsCollector

logger = logging.getLogger(__name__)


class PipelineManager:
    """
    Pipeline Manager that orchestrates data processing workflows through message broker.
    Maintains minimal state and uses complete message-based communication.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            metrics_collector: Optional[MetricsCollector] = None
    ):
        self.message_broker = message_broker
        self.metrics_collector = metrics_collector or MetricsCollector()

        # Component identification
        self.module_identifier = ModuleIdentifier(
            component_name="pipeline_manager",
            component_type=ComponentType.MANAGER,
            department="pipeline",
            role="orchestrator"
        )

        # State tracking
        self.active_pipelines: Dict[str, PipelineContext] = {}

        # Configuration
        self.max_retries = 3
        self.retry_delay = 5  # seconds

        # Initialize handlers
        self._setup_message_handlers()
        logger.info("Pipeline manager initialized")

    def _setup_message_handlers(self) -> None:
        """Initialize message handlers"""
        handlers = {
            MessageType.PIPELINE_START_REQUEST: self._handle_start_request,
            MessageType.STAGE_COMPLETE: self._handle_stage_complete,
            MessageType.STAGE_ERROR: self._handle_stage_error,
            MessageType.STAGE_AWAITING_DECISION: self._handle_stage_awaiting_decision,
            MessageType.DECISION_SUBMITTED: self._handle_decision_submitted,
            MessageType.PIPELINE_PAUSE_REQUEST: self._handle_pause_request,
            MessageType.PIPELINE_RESUME_REQUEST: self._handle_resume_request,
            MessageType.PERSISTENCE_OPERATION_COMPLETE: self._handle_persistence_complete,
            MessageType.PERSISTENCE_OPERATION_FAILED: self._handle_persistence_error,
            MessageType.PIPELINE_STATUS_REQUEST: self._handle_status_request,
            MessageType.PIPELINE_CLEANUP_REQUEST: self._handle_cleanup_request
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.component_name,
                f"{message_type.value}.#",
                handler
            )

    async def initiate_pipeline(
            self,
            config: Dict[str, Any],
            user_id: Optional[str] = None
    ) -> str:
        """Initiate new pipeline processing"""
        pipeline_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())

        # Create context
        context = PipelineContext(
            pipeline_id=pipeline_id,
            correlation_id=correlation_id,
            user_id=user_id,
            stage_configs=config.get('stages', {})
        )
        self.active_pipelines[pipeline_id] = context

        # Request persistence
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.PERSISTENCE_CREATE_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'config': config,
                'user_id': user_id,
                'status': PipelineState.INITIALIZING.value
            },
            metadata=MessageMetadata(
                correlation_id=correlation_id,
                source_component=self.component_name,
                target_component="persistence_manager"
            )
        ))

        return pipeline_id

    async def _start_pipeline_processing(self, pipeline_id: str) -> None:
        """Start pipeline processing after successful persistence"""
        context = self.active_pipelines.get(pipeline_id)
        if not context:
            return

        context.state = PipelineState.RUNNING
        await self._request_stage_processing(
            pipeline_id,
            context.current_stage,
            context.stage_configs.get(context.current_stage.value, {})
        )

    async def _request_stage_processing(
            self,
            pipeline_id: str,
            stage: ProcessingStage,
            config: Dict[str, Any]
    ) -> None:
        """Request processing for a specific stage"""
        target_component = self._get_stage_component(stage)
        context = self.active_pipelines[pipeline_id]

        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGE_START_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'stage': stage.value,
                'config': config
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component=target_component
            )
        ))

    def _get_stage_component(self, stage: ProcessingStage) -> str:
        """Get component responsible for stage"""
        stage_component_mapping = {
            ProcessingStage.QUALITY_CHECK: "quality_manager",
            ProcessingStage.INSIGHT_GENERATION: "insight_manager",
            ProcessingStage.ADVANCED_ANALYTICS: "analytics_manager",
            ProcessingStage.DECISION_MAKING: "decision_manager",
            ProcessingStage.RECOMMENDATION: "recommendation_manager",
            ProcessingStage.REPORT_GENERATION: "report_manager"
        }
        return stage_component_mapping.get(stage, "quality_manager")

    async def _handle_stage_complete(self, message: ProcessingMessage) -> None:
        """Handle stage completion"""
        pipeline_id = message.content['pipeline_id']
        completed_stage = message.content['stage']

        context = self.active_pipelines.get(pipeline_id)
        if not context:
            return

        # Record completion
        context.complete_stage(completed_stage)

        # Request next stage determination
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGE_SEQUENCE_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'completed_stage': completed_stage,
                'completed_stages': context.stages_completed
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="stage_coordinator"
            )
        ))

    async def _handle_stage_error(self, message: ProcessingMessage) -> None:
        """Handle stage processing errors"""
        pipeline_id = message.content['pipeline_id']
        error = message.content['error']
        retry_count = message.content.get('retry_count', 0)

        context = self.active_pipelines.get(pipeline_id)
        if not context:
            return

        if retry_count < self.max_retries:
            await self._attempt_stage_recovery(message)
        else:
            await self._handle_permanent_failure(message)

    async def _attempt_stage_recovery(self, message: ProcessingMessage) -> None:
        """Attempt to recover from stage failure"""
        pipeline_id = message.content['pipeline_id']
        retry_count = message.content.get('retry_count', 0) + 1

        await asyncio.sleep(self.retry_delay)

        context = self.active_pipelines[pipeline_id]
        await self._request_stage_processing(
            pipeline_id,
            context.current_stage,
            context.stage_configs.get(context.current_stage.value, {}),
            retry_count=retry_count
        )

    async def _handle_permanent_failure(self, message: ProcessingMessage) -> None:
        """Handle permanent pipeline failure"""
        pipeline_id = message.content['pipeline_id']
        error = message.content['error']

        context = self.active_pipelines.get(pipeline_id)
        if not context:
            return

        context.state = PipelineState.FAILED
        context.error = error

        # Notify persistence
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.PERSISTENCE_UPDATE_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'status': PipelineState.FAILED.value,
                'error': error
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="persistence_manager"
            )
        ))

        # Notify components
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.PIPELINE_ERROR,
            content={
                'pipeline_id': pipeline_id,
                'error': error
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="broadcast"
            )
        ))

    async def cleanup(self) -> None:
        """Perform cleanup"""
        try:
            for pipeline_id, context in list(self.active_pipelines.items()):
                await self.message_broker.publish(ProcessingMessage(
                    message_type=MessageType.PIPELINE_CLEANUP,
                    content={
                        'pipeline_id': pipeline_id,
                        'reason': 'System shutdown'
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="broadcast"
                    )
                ))

            self.active_pipelines.clear()

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise