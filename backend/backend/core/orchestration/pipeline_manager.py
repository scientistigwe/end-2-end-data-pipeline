# backend/core/managers/pipeline_manager.py

import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

from backend.core.base.base_manager import BaseManager, ResourceState, ChannelType
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage, ProcessingStatus

# Channel Handlers - Central point of channel communication
from backend.core.channel_handlers.data_source_handler import DataSourceChannelHandler
from backend.core.channel_handlers.processing_handler import ProcessingChannelHandler
from backend.core.channel_handlers.decision_handler import DecisionChannelHandler
from backend.core.channel_handlers.insight_handler import InsightChannelHandler
from backend.core.channel_handlers.routing_handler import RoutingChannelHandler
from backend.core.channel_handlers.staging_handler import StagingChannelHandler

logger = logging.getLogger(__name__)


@dataclass
class PipelineState:
    """Pipeline state with enhanced tracking"""
    pipeline_id: str
    source_type: str
    current_stage: str
    status: ProcessingStatus
    metadata: Dict[str, Any]
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    stages_completed: List[str] = field(default_factory=list)
    stages_duration: Dict[str, float] = field(default_factory=dict)
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    retry_attempts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    current_progress: float = 0.0


class PipelineManager(BaseManager):
    """
    Enhanced pipeline manager serving as central orchestrator for all data processing
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "PipelineManager")

        # Initialize channel handlers
        self.channel_handlers = self._initialize_channel_handlers()

        # Pipeline state management
        self.active_pipelines: Dict[str, PipelineState] = {}

        # Register message handlers for each channel
        self._register_channel_handlers()

    def _initialize_channel_handlers(self) -> Dict[str, Any]:
        """Initialize all channel handlers"""
        return {
            ChannelType.DATA_SOURCE: DataSourceChannelHandler(self.message_broker),
            ChannelType.PROCESSING: ProcessingChannelHandler(self.message_broker),
            ChannelType.DECISION: DecisionChannelHandler(self.message_broker),
            ChannelType.INSIGHT: InsightChannelHandler(self.message_broker),
            ChannelType.ROUTING: RoutingChannelHandler(self.message_broker),
            ChannelType.STAGING: StagingChannelHandler(self.message_broker)
        }

    def _register_channel_handlers(self) -> None:
        """Register handlers for all channels"""
        # Data Source Channel
        self._register_data_source_handlers()

        # Processing Channel
        self._register_processing_handlers()

        # Decision Channel
        self._register_decision_handlers()

        # Insight Channel
        self._register_insight_handlers()

        # Routing Channel
        self._register_routing_handlers()

        # Staging Channel
        self._register_staging_handlers()

    def handle_pipeline_request(self, message: ProcessingMessage) -> str:
        """Entry point for new pipeline requests"""
        try:
            # Create pipeline instance
            pipeline_id = str(uuid.uuid4())
            source_type = message.content.get('source_type', 'unknown')

            # Initialize pipeline state
            pipeline_state = PipelineState(
                pipeline_id=pipeline_id,
                source_type=source_type,
                current_stage="initialization",
                status=ProcessingStatus.PENDING,
                metadata=self._extract_metadata(message)
            )

            self.active_pipelines[pipeline_id] = pipeline_state

            # Route to appropriate source handler
            self.channel_handlers[ChannelType.DATA_SOURCE].handle_source_request(
                pipeline_id,
                source_type,
                message.content
            )

            return pipeline_id

        except Exception as e:
            self.logger.error(f"Failed to create pipeline: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def _register_data_source_handlers(self) -> None:
        """Register data source channel handlers"""
        handlers = {
            'new_data': self._handle_new_data,
            'source_error': self._handle_source_error,
            'source_complete': self._handle_source_complete
        }

        for event, handler in handlers.items():
            self.channel_handlers[ChannelType.DATA_SOURCE].register_callback(event, handler)

    def _register_processing_handlers(self) -> None:
        """Register processing channel handlers"""
        handlers = {
            'stage_complete': self._handle_stage_complete,
            'processing_error': self._handle_processing_error,
            'quality_check_complete': self._handle_quality_complete
        }

        for event, handler in handlers.items():
            self.channel_handlers[ChannelType.PROCESSING].register_callback(event, handler)

    def _handle_new_data(self, message: ProcessingMessage) -> None:
        """Handle new data arrival"""
        pipeline_id = message.content['pipeline_id']
        pipeline = self.active_pipelines.get(pipeline_id)

        if not pipeline:
            self.logger.error(f"No pipeline found for id: {pipeline_id}")
            return

        try:
            # Stage the data
            staging_id = self.channel_handlers[ChannelType.STAGING].stage_data(
                pipeline_id,
                message.content['data'],
                message.content.get('metadata', {})
            )

            # Route to processing
            self.channel_handlers[ChannelType.PROCESSING].start_processing(
                pipeline_id,
                staging_id
            )

            # Update pipeline state
            pipeline.status = ProcessingStatus.PROCESSING
            pipeline.current_stage = "data_ingestion"

        except Exception as e:
            self._handle_pipeline_error(pipeline_id, "data_ingestion", e)

    def _handle_stage_complete(self, message: ProcessingMessage) -> None:
        """Handle processing stage completion"""
        pipeline_id = message.content['pipeline_id']
        stage = message.content['stage']
        pipeline = self.active_pipelines.get(pipeline_id)

        if not pipeline:
            return

        try:
            # Update pipeline state
            pipeline.stages_completed.append(stage)
            pipeline.stages_duration[stage] = message.content.get('duration', 0)

            # Get next stage from routing
            next_stage = self.channel_handlers[ChannelType.ROUTING].get_next_stage(
                pipeline_id,
                stage
            )

            if next_stage:
                self._start_next_stage(pipeline_id, next_stage)
            else:
                self._finalize_pipeline(pipeline_id)

        except Exception as e:
            self._handle_pipeline_error(pipeline_id, stage, e)

    def _handle_quality_complete(self, message: ProcessingMessage) -> None:
        """Handle quality check completion"""
        pipeline_id = message.content['pipeline_id']
        quality_status = message.content['quality_status']
        report = message.content.get('report', {})

        try:
            if quality_status == 'passed':
                self._continue_processing(pipeline_id)
            else:
                self._request_quality_decision(pipeline_id, report)

        except Exception as e:
            self._handle_pipeline_error(pipeline_id, "quality_check", e)

    def _start_next_stage(self, pipeline_id: str, stage: str) -> None:
        """Start next processing stage"""
        pipeline = self.active_pipelines.get(pipeline_id)
        if not pipeline:
            return

        pipeline.current_stage = stage

        # Route to appropriate handler based on stage type
        if stage.startswith('quality_'):
            self.channel_handlers[ChannelType.PROCESSING].start_quality_check(pipeline_id)
        elif stage.startswith('insight_'):
            self.channel_handlers[ChannelType.INSIGHT].generate_insights(pipeline_id)
        else:
            self.channel_handlers[ChannelType.PROCESSING].start_stage(pipeline_id, stage)

    def _finalize_pipeline(self, pipeline_id: str) -> None:
        """Finalize pipeline processing"""
        pipeline = self.active_pipelines.get(pipeline_id)
        if not pipeline:
            return

        try:
            # Generate final insights
            self.channel_handlers[ChannelType.INSIGHT].generate_final_insights(
                pipeline_id,
                pipeline.stages_completed,
                pipeline.metadata
            )

            # Update pipeline state
            pipeline.status = ProcessingStatus.COMPLETED
            pipeline.end_time = datetime.now()

            # Clean up resources
            self._cleanup_pipeline_resources(pipeline_id)

        except Exception as e:
            self._handle_pipeline_error(pipeline_id, "finalization", e)

    def _cleanup_pipeline_resources(self, pipeline_id: str) -> None:
        """Clean up pipeline resources"""
        for handler in self.channel_handlers.values():
            handler.cleanup_pipeline(pipeline_id)

        if pipeline_id in self.active_pipelines:
            del self.active_pipelines[pipeline_id]

    def _handle_pipeline_error(self, pipeline_id: str, stage: str, error: Exception) -> None:
        """Handle pipeline processing errors"""
        pipeline = self.active_pipelines.get(pipeline_id)
        if not pipeline:
            return

        error_details = self.handle_error(error, {
            'pipeline_id': pipeline_id,
            'stage': stage,
            'pipeline_state': pipeline.status.value
        })

        pipeline.error_history.append(error_details)

        if pipeline.retry_attempts[stage] < 3:
            pipeline.retry_attempts[stage] += 1
            self._retry_stage(pipeline_id, stage)
        else:
            self._handle_critical_failure(pipeline_id, stage)

    def __del__(self):
        """Cleanup on deletion"""
        for pipeline_id in list(self.active_pipelines.keys()):
            self._cleanup_pipeline_resources(pipeline_id)
        super().__del__()