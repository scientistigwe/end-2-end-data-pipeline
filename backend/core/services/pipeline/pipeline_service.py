import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    PipelineContext,
    PipelineState,
    ComponentType,
    ModuleIdentifier
)

logger = logging.getLogger(__name__)


class PipelineService:
    """
    Service layer for pipeline orchestration.
    Coordinates business logic between components through handler layer.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        self.module_identifier = ModuleIdentifier(
            component_name="pipeline_service",
            component_type=ComponentType.PIPELINE_SERVICE,
            department="pipeline",
            role="service"
        )

        # Active pipelines
        self.active_contexts: Dict[str, PipelineContext] = {}

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup message handling for service layer"""
        handlers = {
            # From Manager
            MessageType.PIPELINE_SERVICE_START: self._handle_service_start,
            MessageType.PIPELINE_SERVICE_STOP: self._handle_service_stop,
            MessageType.PIPELINE_SERVICE_PAUSE: self._handle_service_pause,
            MessageType.PIPELINE_SERVICE_RESUME: self._handle_service_resume,

            # Stage Transitions
            MessageType.PIPELINE_STAGE_COMPLETE: self._handle_stage_complete,
            MessageType.PIPELINE_STAGE_ERROR: self._handle_stage_error,

            # Component Coordination
            MessageType.QUALITY_SERVICE_COMPLETE: self._handle_quality_complete,
            MessageType.INSIGHT_SERVICE_COMPLETE: self._handle_insight_complete,
            MessageType.ANALYTICS_SERVICE_COMPLETE: self._handle_analytics_complete,
            MessageType.DECISION_SERVICE_COMPLETE: self._handle_decision_complete,
            MessageType.RECOMMENDATION_SERVICE_COMPLETE: self._handle_recommendation_complete,
            MessageType.REPORT_SERVICE_COMPLETE: self._handle_report_complete,

            # Monitoring & Health
            MessageType.MONITORING_SERVICE_UPDATE: self._handle_monitoring_update,
            MessageType.MONITORING_SERVICE_ALERT: self._handle_monitoring_alert,

            # Resource Management
            MessageType.RESOURCE_ACCESS_GRANT: self._handle_resource_granted,
            MessageType.RESOURCE_ACCESS_DENY: self._handle_resource_denied
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                f"pipeline.{message_type.value}",
                handler
            )

    async def _handle_service_start(self, message: ProcessingMessage) -> None:
        """Handle pipeline service start request"""
        try:
            pipeline_id = message.content['pipeline_id']
            config = message.content.get('config', {})

            # Create service context
            context = PipelineContext(
                pipeline_id=pipeline_id,
                correlation_id=message.metadata.correlation_id,
                state=PipelineState.INITIALIZING,
                stage_sequence=self._get_stage_sequence(config),
                stage_dependencies=self._get_stage_dependencies()
            )

            self.active_contexts[pipeline_id] = context

            # Start monitoring
            await self._start_monitoring(pipeline_id, config)

            # Initialize first stage
            await self._initialize_first_stage(pipeline_id, config)

        except Exception as e:
            logger.error(f"Failed to handle service start: {str(e)}")
            await self._handle_error(message, str(e))

    async def _start_monitoring(self, pipeline_id: str, config: Dict[str, Any]) -> None:
        """Start pipeline monitoring"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.MONITORING_SERVICE_START,
                content={
                    'pipeline_id': pipeline_id,
                    'config': {
                        'metric_types': ['system', 'performance', 'resource'],
                        'interval': 60,
                        'thresholds': config.get('monitoring_thresholds', {})
                    }
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="monitoring_handler"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _initialize_first_stage(self, pipeline_id: str, config: Dict[str, Any]) -> None:
        """Initialize first pipeline stage"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        # Start with quality check
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.QUALITY_SERVICE_START,
                content={
                    'pipeline_id': pipeline_id,
                    'config': config.get('quality_config', {})
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="pipeline_handler"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_stage_complete(self, message: ProcessingMessage) -> None:
        """Handle stage completion and determine next stage"""
        try:
            pipeline_id = message.content['pipeline_id']
            completed_stage = message.content['stage']
            results = message.content.get('results', {})

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Update context
            context.complete_stage(completed_stage)

            # Determine next stage
            next_stage = self._get_next_stage(context, completed_stage)
            if next_stage:
                await self._initiate_stage(pipeline_id, next_stage, results)
            else:
                await self._complete_pipeline(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle stage completion: {str(e)}")
            await self._handle_error(message, str(e))

    async def _initiate_stage(
            self,
            pipeline_id: str,
            stage: ProcessingStage,
            previous_results: Dict[str, Any]
    ) -> None:
        """Initiate processing for next stage"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        # Get stage-specific message type
        message_type = self._get_stage_message_type(stage)

        # Get stage-specific config
        stage_config = context.stage_configs.get(stage.value, {})

        # Forward to handler
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=message_type,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': stage.value,
                    'config': stage_config,
                    'previous_results': previous_results
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="pipeline_handler"
                ),
                source_identifier=self.module_identifier
            )
        )

    def _get_stage_message_type(self, stage: ProcessingStage) -> MessageType:
        """Get appropriate message type for stage"""
        stage_messages = {
            ProcessingStage.QUALITY_CHECK: MessageType.QUALITY_SERVICE_START,
            ProcessingStage.INSIGHT_GENERATION: MessageType.INSIGHT_SERVICE_START,
            ProcessingStage.ADVANCED_ANALYTICS: MessageType.ANALYTICS_SERVICE_START,
            ProcessingStage.DECISION_MAKING: MessageType.DECISION_SERVICE_START,
            ProcessingStage.RECOMMENDATION: MessageType.RECOMMENDATION_SERVICE_START,
            ProcessingStage.REPORT_GENERATION: MessageType.REPORT_SERVICE_START
        }
        return stage_messages.get(stage)

    async def _handle_monitoring_update(self, message: ProcessingMessage) -> None:
        """Handle monitoring updates"""
        try:
            pipeline_id = message.content['pipeline_id']
            metrics = message.content['metrics']

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Update metrics in context
            context.update_metrics(metrics)

            # Check for resource constraints
            if self._check_resource_constraints(metrics):
                await self._handle_resource_constraint(pipeline_id, metrics)

            # Forward to handler
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_METRICS_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'metrics': metrics
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to handle monitoring update: {str(e)}")
            await self._handle_error(message, str(e))

    async def _complete_pipeline(self, pipeline_id: str) -> None:
        """Handle pipeline completion"""
        try:
            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Generate final report
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_SERVICE_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'stage_results': context.stage_results,
                        'metrics': context.metrics
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Stop monitoring
            await self._stop_monitoring(pipeline_id)

            # Cleanup
            await self._cleanup_pipeline(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to complete pipeline: {str(e)}")
            await self._handle_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                str(e)
            )

    async def _stop_monitoring(self, pipeline_id: str) -> None:
        """Stop pipeline monitoring"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.MONITORING_SERVICE_STOP,
                content={
                    'pipeline_id': pipeline_id
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="monitoring_handler"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_error(self, message: ProcessingMessage, error: str) -> None:
        """Handle service-level errors"""
        pipeline_id = message.content.get('pipeline_id')
        if not pipeline_id:
            return

        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_SERVICE_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup
            await self._cleanup_pipeline(pipeline_id)

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    async def _cleanup_pipeline(self, pipeline_id: str) -> None:
        """Cleanup pipeline resources"""
        if pipeline_id in self.active_contexts:
            del self.active_contexts[pipeline_id]

    def _get_stage_sequence(self, config: Dict[str, Any]) -> list:
        """Get configured stage sequence"""
        default_sequence = [
            ProcessingStage.QUALITY_CHECK,
            ProcessingStage.INSIGHT_GENERATION,
            ProcessingStage.ADVANCED_ANALYTICS,
            ProcessingStage.DECISION_MAKING,
            ProcessingStage.RECOMMENDATION,
            ProcessingStage.REPORT_GENERATION
        ]
        return config.get('stage_sequence', default_sequence)

    def _get_stage_dependencies(self) -> Dict[str, list]:
        """Get stage dependencies"""
        return {
            ProcessingStage.INSIGHT_GENERATION.value: [ProcessingStage.QUALITY_CHECK.value],
            ProcessingStage.ADVANCED_ANALYTICS.value: [ProcessingStage.QUALITY_CHECK.value],
            ProcessingStage.DECISION_MAKING.value: [ProcessingStage.INSIGHT_GENERATION.value],
            ProcessingStage.RECOMMENDATION.value: [ProcessingStage.DECISION_MAKING.value],
            ProcessingStage.REPORT_GENERATION.value: [ProcessingStage.RECOMMENDATION.value]
        }

    async def cleanup(self) -> None:
        """Cleanup service resources"""
        try:
            # Stop all active pipelines
            for pipeline_id in list(self.active_contexts.keys()):
                await self._stop_monitoring(pipeline_id)
                await self._cleanup_pipeline(pipeline_id)

        except Exception as e:
            logger.error(f"Service cleanup failed: {str(e)}")
            raise