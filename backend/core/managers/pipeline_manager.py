# backend/core/orchestration/pipeline_manager.py

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Coroutine
from uuid import UUID, uuid4
from datetime import datetime
import asyncio
import contextlib
import uuid


from core.messaging.broker import MessageBroker
from core.control.cpm import ControlPointManager
from core.staging.staging_manager import StagingManager
from core.monitoring.process import ProcessMonitor
from core.monitoring.collectors import MetricsCollector

# Import domain-specific managers
from core.managers.quality_manager import QualityManager
from core.managers.insight_manager import InsightManager
from core.managers.decision_manager import DecisionManager
from core.managers.recommendation_manager import RecommendationManager
from core.managers.report_manager import ReportManager
from core.managers.advanced_analytics_manager import AdvancedAnalyticsManager

from ..messaging.event_types import (
    MessageType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage,
    ModuleIdentifier,
    ComponentType,
    ProcessingContext
)

from db.repository.pipeline_repository import PipelineRepository

logger = logging.getLogger(__name__)


class PipelineManager:
    """
    Comprehensive Pipeline Orchestration Manager

    Responsible for coordinating processing across different domain managers,
    managing pipeline lifecycle, and ensuring smooth inter-manager communication.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            repository: PipelineRepository,
            staging_manager: StagingManager,
            control_point_manager: ControlPointManager,
            metrics_collector: Optional[MetricsCollector] = None
    ):
        """
        Initialize Pipeline Manager with core system components

        Args:
            message_broker: Message communication system
            repository: Database repository for pipeline operations
            staging_manager: Manages data staging across pipeline
            control_point_manager: Manages control points and decisions
            metrics_collector: Optional metrics collection system
        """
        # Core system components
        self.message_broker = message_broker
        self.repository = repository
        self.staging_manager = staging_manager
        self.control_point_manager = control_point_manager
        self.metrics_collector = metrics_collector or MetricsCollector()

        # Process monitoring
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="pipeline_manager",
            source_id=str(uuid4())
        )

        # Initialize domain-specific managers
        self.managers = {
            'quality': QualityManager(message_broker, control_point_manager),
            'insight': InsightManager(message_broker, control_point_manager),
            'decision': DecisionManager(message_broker, control_point_manager),
            'recommendation': RecommendationManager(message_broker, control_point_manager),
            'report': ReportManager(message_broker, control_point_manager),
            'analytics': AdvancedAnalyticsManager(message_broker, control_point_manager)
        }

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="PipelineManager",
            component_type=ComponentType.MANAGER,
            method_name="orchestrate_pipeline"
        )

        # Active pipeline tracking
        self.active_pipelines: Dict[str, Dict[str, Any]] = {}

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self):
        """
        Setup message handlers for different pipeline-related events
        """
        handlers = {
            MessageType.PIPELINE_START: self._handle_pipeline_start,
            MessageType.PIPELINE_STAGE_START: self._handle_stage_start,
            MessageType.PIPELINE_STAGE_COMPLETE: self._handle_stage_complete,
            MessageType.PIPELINE_ERROR: self._handle_pipeline_error,
            MessageType.PIPELINE_PAUSE: self._handle_pipeline_pause,
            MessageType.PIPELINE_RESUME: self._handle_pipeline_resume
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                component=self.module_identifier.component_name,
                pattern=f"{message_type.value}.#",
                callback=handler
            )

    async def orchestrate_pipeline(
            self,
            pipeline_config: Dict[str, Any],
            user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Orchestrate a complete pipeline processing workflow

        Args:
            pipeline_config: Configuration for the pipeline
            user_id: Optional user identifier

        Returns:
            Dictionary with pipeline processing results
        """
        try:
            # Generate unique pipeline ID
            pipeline_id = str(uuid4())

            # Create pipeline record in repository
            pipeline_record = await self.repository.create_pipeline({
                'id': pipeline_id,
                'config': pipeline_config,
                'user_id': user_id,
                'status': ProcessingStatus.PENDING.value
            })

            # Create initial pipeline context
            pipeline_context = {
                'id': pipeline_id,
                'config': pipeline_config,
                'user_id': user_id,
                'status': ProcessingStatus.PENDING,
                'current_stage': ProcessingStage.INITIAL_VALIDATION,
                'stages_completed': [],
                'created_at': datetime.utcnow()
            }
            self.active_pipelines[pipeline_id] = pipeline_context

            # Publish pipeline start event
            start_message = ProcessingMessage(
                source_identifier=self.module_identifier,
                message_type=MessageType.PIPELINE_START,
                content={
                    'pipeline_id': pipeline_id,
                    'config': pipeline_config,
                    'user_id': user_id
                }
            )
            await self.message_broker.publish(start_message)

            return {
                'status': 'success',
                'pipeline_id': pipeline_id,
                'message': 'Pipeline initialization started'
            }

        except Exception as e:
            logger.error(f"Pipeline orchestration error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _handle_pipeline_start(self, message: ProcessingMessage):
        """
        Handle initial pipeline start event
        Initiate first stage of processing
        """
        try:
            pipeline_id = message.content['pipeline_id']
            pipeline_context = self.active_pipelines[pipeline_id]

            # Update pipeline status
            pipeline_context['status'] = ProcessingStatus.RUNNING
            await self.repository.update_pipeline_status(
                pipeline_id,
                ProcessingStatus.RUNNING.value
            )

            # Trigger first stage (Initial Validation)
            await self._trigger_next_stage(pipeline_id)

        except Exception as e:
            await self._handle_pipeline_error(message, e)

    async def _trigger_next_stage(self, pipeline_id: str):
        """
        Trigger the next processing stage based on pipeline configuration
        """
        context = self.active_pipelines[pipeline_id]
        config = context['config']
        current_stage = context['current_stage']

        # Mapping of stages to managers
        stage_manager_mapping = {
            ProcessingStage.INITIAL_VALIDATION: self.managers['quality'],
            ProcessingStage.QUALITY_CHECK: self.managers['quality'],
            ProcessingStage.CONTEXT_ANALYSIS: self.managers['insight'],
            ProcessingStage.INSIGHT_GENERATION: self.managers['insight'],
            ProcessingStage.ADVANCED_ANALYTICS: self.managers['analytics'],
            ProcessingStage.DECISION_MAKING: self.managers['decision'],
            ProcessingStage.RECOMMENDATION: self.managers['recommendation'],
            ProcessingStage.REPORT_GENERATION: self.managers['report']
        }

        # Get appropriate manager for current stage
        manager = stage_manager_mapping.get(current_stage)
        if not manager:
            raise ValueError(f"No manager configured for stage: {current_stage}")

        # Prepare stage-specific configuration
        stage_config = config.get('stages', {}).get(current_stage.value, {})

        # Create stage start message
        stage_message = ProcessingMessage(
            source_identifier=self.module_identifier,
            message_type=MessageType.PIPELINE_STAGE_START,
            content={
                'pipeline_id': pipeline_id,
                'stage': current_stage.value,
                'config': stage_config
            }
        )
        await self.message_broker.publish(stage_message)

    async def _handle_stage_complete(self, message: ProcessingMessage):
        """
        Handle completion of a pipeline stage
        Determine and trigger next stage or complete pipeline
        """
        try:
            pipeline_id = message.content['pipeline_id']
            completed_stage = ProcessingStage(message.content['stage'])

            context = self.active_pipelines[pipeline_id]
            context['stages_completed'].append(completed_stage.value)

            # Determine next stage based on configuration
            next_stage = self._get_next_stage(context['config'], completed_stage)

            if next_stage:
                # Update current stage and trigger next stage
                context['current_stage'] = next_stage
                await self._trigger_next_stage(pipeline_id)
            else:
                # Pipeline complete
                await self._complete_pipeline(pipeline_id)

        except Exception as e:
            await self._handle_pipeline_error(message, e)

    def _get_next_stage(
            self,
            pipeline_config: Dict[str, Any],
            current_stage: ProcessingStage
    ) -> Optional[ProcessingStage]:
        """
        Determine the next processing stage
        """
        stages = list(ProcessingStage)
        current_index = stages.index(current_stage)

        # Return next stage if available
        return stages[current_index + 1] if current_index + 1 < len(stages) else None

    async def _complete_pipeline(self, pipeline_id: str):
        """
        Handle successful pipeline completion
        """
        try:
            context = self.active_pipelines[pipeline_id]
            context['status'] = ProcessingStatus.COMPLETED
            context['completed_at'] = datetime.utcnow()

            # Update repository
            await self.repository.update_pipeline_status(
                pipeline_id,
                ProcessingStatus.COMPLETED.value
            )

            # Cleanup
            del self.active_pipelines[pipeline_id]

        except Exception as e:
            logger.error(f"Pipeline completion error: {str(e)}")

    async def _handle_pipeline_error(
            self,
            message: ProcessingMessage,
            error: Optional[Exception] = None
    ):
        """
        Handle pipeline processing errors
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            if pipeline_id and pipeline_id in self.active_pipelines:
                context = self.active_pipelines[pipeline_id]
                context['status'] = ProcessingStatus.FAILED
                context['error'] = str(error) if error else "Unknown error"

                # Update repository
                await self.repository.update_pipeline_status(
                    pipeline_id,
                    ProcessingStatus.FAILED.value,
                    error=str(error)
                )

                # Cleanup
                del self.active_pipelines[pipeline_id]

        except Exception as e:
            logger.error(f"Error handling pipeline error: {str(e)}")

    async def _handle_pipeline_pause(self, message: ProcessingMessage):
        """Handle pipeline pause request"""
        try:
            pipeline_id = message.content['pipeline_id']
            context = self.active_pipelines[pipeline_id]
            context['status'] = ProcessingStatus.PAUSED

            await self.repository.update_pipeline_status(
                pipeline_id,
                ProcessingStatus.PAUSED.value
            )

        except Exception as e:
            logger.error(f"Pipeline pause error: {str(e)}")

    async def _handle_pipeline_resume(self, message: ProcessingMessage):
        """Handle pipeline resume request"""
        try:
            pipeline_id = message.content['pipeline_id']
            context = self.active_pipelines[pipeline_id]
            context['status'] = ProcessingStatus.RUNNING

            await self.repository.update_pipeline_status(
                pipeline_id,
                ProcessingStatus.RUNNING.value
            )

            # Continue from last stage
            await self._trigger_next_stage(pipeline_id)

        except Exception as e:
            logger.error(f"Pipeline resume error: {str(e)}")

    async def cleanup(self):
        """
        Cleanup active pipelines and resources
        """
        try:
            # Cancel all active pipelines
            for pipeline_id in list(self.active_pipelines.keys()):
                await self._handle_pipeline_error(
                    ProcessingMessage(
                        content={'pipeline_id': pipeline_id}
                    ),
                    Exception("System shutdown")
                )
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")


def _setup_message_handlers(self) -> None:
    """
    Setup initial message handlers for the base manager.
    This method should be overridden by subclasses to define
    specific message handling behavior.
    """
    # Define a default set of handlers for base error and lifecycle management
    handlers = {
        MessageType.COMPONENT_INIT: self._handle_component_init,
        MessageType.COMPONENT_UPDATE: self._handle_component_update,
        MessageType.COMPONENT_ERROR: self._handle_component_error,
        MessageType.COMPONENT_SYNC: self._handle_component_sync
    }

    for message_type, handler in handlers.items():
        asyncio.create_task(
            self.message_broker.subscribe(
                component=self.component_name,
                pattern=f"{self.domain_type}.{message_type.value}.#",
                callback=handler
            )
        )


async def _handle_component_init(self, message: ProcessingMessage) -> None:
    """
    Handle component initialization messages

    Args:
        message (ProcessingMessage): Initialization message
    """
    try:
        # Log initialization
        self.logger.info(f"Component initialization: {message.content}")

        # Create processing context
        context = ProcessingContext(
            pipeline_id=message.content.get('pipeline_id', str(uuid.uuid4())),
            stage=ProcessingStage.INITIAL_VALIDATION,
            status=ProcessingStatus.PENDING,
            metadata=message.content.get('metadata', {})
        )

        # Add to active processes
        self.add_active_process(context.request_id, context)

    except Exception as e:
        self.logger.error(f"Component initialization error: {str(e)}")
        await self._handle_error(message, e)


async def _handle_component_update(self, message: ProcessingMessage) -> None:
    """
    Handle component update messages

    Args:
        message (ProcessingMessage): Update message
    """
    try:
        # Find and update existing context
        context_id = message.content.get('request_id')
        if context_id and context_id in self._active_processes:
            context = self._active_processes[context_id]

            # Update context with new information
            context.metadata.update(message.content.get('metadata', {}))
            context.record_step({
                'event': 'component_update',
                'details': message.content
            })

            self.logger.info(f"Component update processed: {context_id}")

    except Exception as e:
        self.logger.error(f"Component update error: {str(e)}")
        await self._handle_error(message, e)


async def _handle_component_error(self, message: ProcessingMessage) -> None:
    """
    Handle component error messages

    Args:
        message (ProcessingMessage): Error message
    """
    try:
        context_id = message.content.get('request_id')
        error = message.content.get('error', 'Unknown error')

        # Find and update context if exists
        if context_id and context_id in self._active_processes:
            context = self._active_processes[context_id]
            context.error = error
            context.update_status(ProcessingStatus.FAILED)
            context.add_warning(error)

        # Log the error
        self.logger.error(f"Component error: {error}")

        # Potentially trigger error handling workflow
        await self._handle_error(message, Exception(error))

    except Exception as e:
        self.logger.error(f"Error handling component error: {str(e)}")


async def _handle_component_sync(self, message: ProcessingMessage) -> None:
    """
    Handle component synchronization messages

    Args:
        message (ProcessingMessage): Sync message
    """
    try:
        # Log sync event
        self.logger.info(f"Component sync received: {message.content}")

        # Perform any necessary synchronization
        context_id = message.content.get('request_id')
        if context_id and context_id in self._active_processes:
            context = self._active_processes[context_id]
            context.record_step({
                'event': 'component_sync',
                'details': message.content
            })

    except Exception as e:
        self.logger.error(f"Component sync error: {str(e)}")
        await self._handle_error(message, e)


def add_active_process(self, process_id: str, context: ProcessingContext) -> None:
    """
    Add an active process to the manager's tracking

    Args:
        process_id (str): Unique identifier for the process
        context (ProcessingContext): Processing context for the process
    """
    with contextlib.suppress(Exception):
        self._active_processes[process_id] = context
        self.metrics.active_processes += 1


def remove_active_process(self, process_id: str) -> None:
    """
    Remove an active process from the manager's tracking

    Args:
        process_id (str): Unique identifier for the process to remove
    """
    with contextlib.suppress(Exception):
        if process_id in self._active_processes:
            del self._active_processes[process_id]
            self.metrics.active_processes = max(0, self.metrics.active_processes - 1)


def get_active_process(self, process_id: str) -> Optional[ProcessingContext]:
    """
    Retrieve an active process context

    Args:
        process_id (str): Unique identifier for the process

    Returns:
        Optional[ProcessingContext]: Processing context if found, None otherwise
    """
    return self._active_processes.get(process_id)


def get_active_processes(self) -> Dict[str, ProcessingContext]:
    """
    Retrieve all active processes

    Returns:
        Dict[str, ProcessingContext]: Dictionary of active processes
    """
    return self._active_processes.copy()