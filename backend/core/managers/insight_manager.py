import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    MessageMetadata,
    InsightContext,
    InsightState,
    ManagerState,
    ModuleIdentifier,
    ComponentType,
    InsightMetrics
)
from .base.base_manager import BaseManager

logger = logging.getLogger(__name__)


class InsightManager(BaseManager):
    """
    Insight Manager: Coordinates high-level insight workflow via message-driven communication.
    Manages insight generation, validation, and processing through message broker.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            component_name: str = "insight_manager",
            domain_type: str = "insight"
    ):
        super().__init__(
            message_broker=message_broker,
            component_name=component_name,
            domain_type=domain_type
        )

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name=component_name,
            component_type=ComponentType.INSIGHT_MANAGER,
            department=domain_type,
            role="manager"
        )

        # Active processes and contexts
        self.active_contexts: Dict[str, InsightContext] = {}
        self.process_timeouts: Dict[str, datetime] = {}

        # Configuration
        self.insight_thresholds = {
            "confidence_threshold": 0.8,
            "minimum_support": 0.1,
            "minimum_correlation": 0.3,
            "maximum_processing_time": 3600  # 1 hour
        }

        # Initialize
        self.state = ManagerState.INITIALIZING
        self._initialize_manager()

    def _initialize_manager(self) -> None:
        """Initialize insight manager components"""
        self._setup_message_handlers()
        self._start_background_tasks()
        self.state = ManagerState.ACTIVE

    async def _setup_domain_handlers(self) -> None:
        """Setup insight-specific message handlers"""
        handlers = {
            # Core Flow
            MessageType.INSIGHT_GENERATE_REQUEST: self._handle_generate_request,
            MessageType.INSIGHT_GENERATE_START: self._handle_generate_start,
            MessageType.INSIGHT_GENERATE_PROGRESS: self._handle_generate_progress,
            MessageType.INSIGHT_GENERATE_COMPLETE: self._handle_generate_complete,
            MessageType.INSIGHT_GENERATE_FAILED: self._handle_generate_failed,

            # Context Analysis
            MessageType.INSIGHT_CONTEXT_ANALYZE_REQUEST: self._handle_context_analysis_request,
            MessageType.INSIGHT_CONTEXT_ANALYZE_COMPLETE: self._handle_context_analysis_complete,

            # Detection Process
            MessageType.INSIGHT_DETECTION_START: self._handle_detection_start,
            MessageType.INSIGHT_DETECTION_PROGRESS: self._handle_detection_progress,
            MessageType.INSIGHT_DETECTION_COMPLETE: self._handle_detection_complete,

            # Type-Specific Processing
            MessageType.INSIGHT_PATTERN_PROCESS: self._handle_pattern_process,
            MessageType.INSIGHT_TREND_PROCESS: self._handle_trend_process,
            MessageType.INSIGHT_RELATIONSHIP_PROCESS: self._handle_relationship_process,
            MessageType.INSIGHT_ANOMALY_PROCESS: self._handle_anomaly_process,

            # Validation Flow
            MessageType.INSIGHT_VALIDATE_REQUEST: self._handle_validate_request,
            MessageType.INSIGHT_VALIDATE_COMPLETE: self._handle_validate_complete,
            MessageType.INSIGHT_VALIDATE_FAILED: self._handle_validate_failed,

            # Resource Management
            MessageType.INSIGHT_RESOURCE_REQUEST: self._handle_resource_request,
            MessageType.INSIGHT_RESOURCE_RELEASE: self._handle_resource_release,
            MessageType.INSIGHT_RESOURCE_UNAVAILABLE: self._handle_resource_unavailable,

            # System Operations
            MessageType.INSIGHT_METRICS_UPDATE: self._handle_metrics_update,
            MessageType.INSIGHT_HEALTH_CHECK: self._handle_health_check,
            MessageType.INSIGHT_CONFIG_UPDATE: self._handle_config_update,
            MessageType.INSIGHT_BACKPRESSURE_NOTIFY: self._handle_backpressure_notify
        }

        for message_type, handler in handlers.items():
            await self.register_message_handler(message_type, handler)

    async def _handle_generate_request(self, message: ProcessingMessage) -> None:
        """Handle insight generation request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            config = message.content.get('config', {})

            # Validate configuration
            if not self._validate_insight_config(config):
                raise ValueError("Invalid insight generation configuration")

            # Create insight context
            context = InsightContext(
                pipeline_id=pipeline_id,
                correlation_id=str(uuid.uuid4()),
                state=InsightState.INITIALIZING,
                enabled_features=config.get('enabled_features', []),
                processing_mode=config.get('processing_mode', 'batch')
            )

            self.active_contexts[pipeline_id] = context

            # Start context analysis
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_CONTEXT_ANALYZE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="insight_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Generate request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_context_analysis_request(self, message: ProcessingMessage) -> None:
        """Handle context analysis request"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = InsightState.CONTEXT_ANALYSIS
            context.updated_at = datetime.now()

            # Request context analysis
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_CONTEXT_ANALYZE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'context': context.to_dict()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="insight_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Context analysis request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_pattern_process(self, message: ProcessingMessage) -> None:
        """Handle pattern analysis process"""
        pipeline_id = message.content.get('pipeline_id')
        patterns = message.content.get('patterns', [])
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            # Process patterns
            processed_patterns = await self._process_patterns(patterns)

            # Update context with processed patterns
            context.intermediate_results['patterns'] = processed_patterns

            # Move to next processing stage
            await self._proceed_to_next_stage(pipeline_id, processed_patterns)

        except Exception as e:
            logger.error(f"Pattern processing failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _process_patterns(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and validate discovered patterns"""
        processed_patterns = []

        for pattern in patterns:
            if self._validate_pattern(pattern):
                processed_patterns.append({
                    **pattern,
                    'validated': True,
                    'confidence': self._calculate_pattern_confidence(pattern)
                })

        return processed_patterns

    def _validate_pattern(self, pattern: Dict[str, Any]) -> bool:
        """Validate individual pattern"""
        try:
            # Check required fields
            required_fields = ['type', 'support', 'confidence']
            if not all(field in pattern for field in required_fields):
                return False

            # Validate thresholds
            if pattern['support'] < self.insight_thresholds['minimum_support']:
                return False
            if pattern['confidence'] < self.insight_thresholds['confidence_threshold']:
                return False

            return True

        except Exception as e:
            logger.error(f"Pattern validation failed: {str(e)}")
            return False

    def _calculate_pattern_confidence(self, pattern: Dict[str, Any]) -> float:
        """Calculate confidence score for pattern"""
        try:
            base_confidence = pattern.get('confidence', 0)
            support_weight = pattern.get('support', 0) / self.insight_thresholds['minimum_support']

            return min(base_confidence * support_weight, 1.0)

        except Exception as e:
            logger.error(f"Confidence calculation failed: {str(e)}")
            return 0.0

    async def _handle_trend_process(self, message: ProcessingMessage) -> None:
        """Handle trend analysis process"""
        pipeline_id = message.content.get('pipeline_id')
        trends = message.content.get('trends', [])
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            # Process trends
            processed_trends = await self._process_trends(trends)

            # Update context
            context.intermediate_results['trends'] = processed_trends

            # Move to next stage
            await self._proceed_to_next_stage(pipeline_id, processed_trends)

        except Exception as e:
            logger.error(f"Trend processing failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _process_trends(self, trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and validate discovered trends"""
        processed_trends = []

        for trend in trends:
            if self._validate_trend(trend):
                processed_trends.append({
                    **trend,
                    'validated': True,
                    'significance': self._calculate_trend_significance(trend)
                })

        return processed_trends

    async def _proceed_to_next_stage(self, pipeline_id: str, results: Any) -> None:
        """Proceed to next processing stage"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        try:
            # Determine next stage based on current state
            next_stage = self._determine_next_stage(context)

            if next_stage:
                # Update context state
                context.state = next_stage
                context.updated_at = datetime.now()

                # Publish next stage request
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=self._get_stage_message_type(next_stage),
                        content={
                            'pipeline_id': pipeline_id,
                            'results': results,
                            'context': context.to_dict()
                        },
                        source_identifier=self.module_identifier
                    )
                )
            else:
                # Complete insight generation
                await self._complete_insight_generation(pipeline_id)

        except Exception as e:
            logger.error(f"Stage progression failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    def _determine_next_stage(self, context: InsightContext) -> Optional[InsightState]:
        """Determine next processing stage based on current state"""
        stage_sequence = {
            InsightState.INITIALIZING: InsightState.CONTEXT_ANALYSIS,
            InsightState.CONTEXT_ANALYSIS: InsightState.DETECTION_IN_PROGRESS,
            InsightState.DETECTION_IN_PROGRESS: InsightState.VALIDATION_PENDING,
            InsightState.VALIDATION_PENDING: InsightState.VALIDATION_IN_PROGRESS,
            InsightState.VALIDATION_IN_PROGRESS: InsightState.RESULTS_AGGREGATION,
            InsightState.RESULTS_AGGREGATION: None  # End of sequence
        }

        return stage_sequence.get(context.state)

    def _get_stage_message_type(self, stage: InsightState) -> MessageType:
        """Get message type for stage"""
        stage_messages = {
            InsightState.CONTEXT_ANALYSIS: MessageType.INSIGHT_CONTEXT_ANALYZE_REQUEST,
            InsightState.DETECTION_IN_PROGRESS: MessageType.INSIGHT_DETECTION_START,
            InsightState.VALIDATION_PENDING: MessageType.INSIGHT_VALIDATE_REQUEST,
            InsightState.RESULTS_AGGREGATION: MessageType.INSIGHT_GENERATE_COMPLETE
        }

        return stage_messages.get(stage, MessageType.INSIGHT_GENERATE_STATUS)

    async def _complete_insight_generation(self, pipeline_id: str) -> None:
        """Complete insight generation process"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        try:
            # Aggregate final results
            final_results = self._aggregate_results(context)

            # Update context
            context.state = InsightState.COMPLETION
            context.completed_at = datetime.now()

            # Notify completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_GENERATE_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'results': final_results,
                        'context': context.to_dict()
                    },
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Completion failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    def _aggregate_results(self, context: InsightContext) -> Dict[str, Any]:
        """Aggregate all insight results"""
        return {
            'patterns': context.intermediate_results.get('patterns', []),
            'trends': context.intermediate_results.get('trends', []),
            'relationships': context.intermediate_results.get('relationships', []),
            'anomalies': context.intermediate_results.get('anomalies', []),
            'metrics': context.metrics.__dict__,
            'processing_time': (
                        context.completed_at - context.created_at).total_seconds() if context.completed_at else None
        }

    async def _handle_error(self, pipeline_id: str, error: str) -> None:
        """Handle errors in insight processing"""
        try:
            context = self.active_contexts.get(pipeline_id)
            if context:
                # Update context state
                context.state = InsightState.ERROR
                context.error = error
                context.updated_at = datetime.now()

            # Notify error
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_GENERATE_FAILED,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup process
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    def _start_background_tasks(self) -> None:
        """Start background monitoring tasks"""
        asyncio.create_task(self._monitor_insight_processes())
        asyncio.create_task(self._monitor_resource_usage())
        asyncio.create_task(self._monitor_backpressure())

    async def _monitor_insight_processes(self) -> None:
        """Monitor long-running insight processes"""
        while self.state == ManagerState.ACTIVE:
            try:
                current_time = datetime.now()
                timeout_threshold = current_time - timedelta(hours=1)  # 1-hour timeout

                for pipeline_id, context in list(self.active_contexts.items()):
                    if context.created_at < timeout_threshold:
                        await self._handle_error(
                            pipeline_id,
                            "Insight generation exceeded maximum time limit"
                        )

                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                logger.error(f"Process monitoring failed: {str(e)}")
                await asyncio.sleep(60)

    async def _monitor_resource_usage(self) -> None:
        """Monitor resource usage of insight processes"""
        while self.state == ManagerState.ACTIVE:
            try:
                for pipeline_id, context in self.active_contexts.items():
                    resource_metrics = await self._collect_resource_metrics()

                    if self._exceeds_resource_limits(resource_metrics):
                        await self._handle_resource_violation(pipeline_id, resource_metrics)

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Resource monitoring failed: {str(e)}")
                await asyncio.sleep(30)

    async def _collect_resource_metrics(self) -> Dict[str, float]:
        """Collect resource usage metrics"""
        try:
            import psutil

            process = psutil.Process()
            return {
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'num_threads': process.num_threads(),
                'open_files': len(process.open_files())
            }
        except Exception as e:
            logger.error(f"Resource metrics collection failed: {str(e)}")
            return {}

    def _exceeds_resource_limits(self, metrics: Dict[str, float]) -> bool:
        """Check if resource metrics exceed limits"""
        return any([
            metrics.get('cpu_percent', 0) > 90,
            metrics.get('memory_percent', 0) > 85
        ])

    async def _handle_resource_violation(self, pipeline_id: str, metrics: Dict[str, float]) -> None:
        """Handle resource limit violations"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_RESOURCE_UNAVAILABLE,
                    content={
                        'pipeline_id': pipeline_id,
                        'metrics': metrics,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            logger.error(f"Resource violation handling failed: {str(e)}")

    async def _monitor_backpressure(self) -> None:
        """Monitor system backpressure"""
        while self.state == ManagerState.ACTIVE:
            try:
                active_processes = len(self.active_contexts)
                if active_processes > 10:  # Example threshold
                    await self._handle_backpressure(active_processes)

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Backpressure monitoring failed: {str(e)}")
                await asyncio.sleep(15)

    async def _handle_backpressure(self, active_count: int) -> None:
        """Handle system backpressure"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_BACKPRESSURE_NOTIFY,
                    content={
                        'active_processes': active_count,
                        'threshold': 10,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            logger.error(f"Backpressure handling failed: {str(e)}")

    async def _handle_health_check(self, message: ProcessingMessage) -> None:
        """Handle health check requests"""
        pipeline_id = message.content.get('pipeline_id')

        try:
            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Collect health metrics
            health_metrics = {
                'state': context.state.value,
                'process_duration': (datetime.now() - context.created_at).total_seconds(),
                'resource_usage': await self._collect_resource_metrics(),
                'error_count': len(context.errors),
                'processing_progress': context.progress
            }

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_HEALTH_CHECK,
                    content={
                        'pipeline_id': pipeline_id,
                        'health_metrics': health_metrics,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")

    async def _handle_metrics_update(self, message: ProcessingMessage) -> None:
        """Handle metrics updates"""
        pipeline_id = message.content.get('pipeline_id')
        metrics_update = message.content.get('metrics', {})

        try:
            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Update context metrics
            context.metrics = InsightMetrics(**metrics_update)
            context.updated_at = datetime.now()

            # Check metric thresholds
            if self._check_metric_thresholds(context.metrics):
                await self._handle_metric_threshold_breach(pipeline_id, context.metrics)

        except Exception as e:
            logger.error(f"Metrics update failed: {str(e)}")

    def _check_metric_thresholds(self, metrics: InsightMetrics) -> bool:
        """Check if metrics exceed thresholds"""
        return any([
            metrics.detection_accuracy < self.insight_thresholds.get('minimum_accuracy', 0.7),
            metrics.processing_time > self.insight_thresholds.get('maximum_processing_time', 3600)
        ])

    async def _handle_metric_threshold_breach(self, pipeline_id: str, metrics: InsightMetrics) -> None:
        """Handle metrics threshold breaches"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_METRICS_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'threshold_breach': True,
                        'metrics': metrics.__dict__,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            logger.error(f"Metric threshold breach handling failed: {str(e)}")

    async def _handle_config_update(self, message: ProcessingMessage) -> None:
        """Handle configuration updates"""
        config_updates = message.content.get('config', {})

        try:
            # Update insight thresholds
            if thresholds := config_updates.get('thresholds'):
                self.insight_thresholds.update(thresholds)

            # Notify update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_CONFIG_UPDATE,
                    content={
                        'status': 'completed',
                        'updates': config_updates,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Config update failed: {str(e)}")

    async def _cleanup_process(self, pipeline_id: str) -> None:
        """Cleanup insight process resources"""
        try:
            # Remove context
            if pipeline_id in self.active_contexts:
                del self.active_contexts[pipeline_id]

            # Remove from timeouts
            if pipeline_id in self.process_timeouts:
                del self.process_timeouts[pipeline_id]

        except Exception as e:
            logger.error(f"Process cleanup failed: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup insight manager resources"""
        try:
            # Update state
            self.state = ManagerState.SHUTDOWN

            # Clean up all active processes
            for pipeline_id in list(self.active_contexts.keys()):
                await self._cleanup_process(pipeline_id)

            # Clear all data
            self.active_contexts.clear()
            self.process_timeouts.clear()

            # Cleanup base manager resources
            await super().cleanup()

        except Exception as e:
            logger.error(f"Insight manager cleanup failed: {str(e)}")
            raise