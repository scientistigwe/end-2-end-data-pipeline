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

        # Initialize state
        self.state = ManagerState.INITIALIZING

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
        """Monitor resource usage"""
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

            # Request context analysis
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_CONTEXT_ANALYZE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="insight_service"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Generate request failed: {str(e)}")
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
            required_fields = ['type', 'support', 'confidence']
            if not all(field in pattern for field in required_fields):
                return False

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

    async def _proceed_to_next_stage(self, pipeline_id: str, results: Any) -> None:
        """Proceed to next processing stage"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        try:
            next_stage = self._determine_next_stage(context)

            if next_stage:
                context.state = next_stage
                context.updated_at = datetime.now()

                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=self._get_stage_message_type(next_stage),
                        content={
                            'pipeline_id': pipeline_id,
                            'results': results,
                            'context': context.to_dict()
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component="insight_service"
                        )
                    )
                )
            else:
                await self._complete_insight_generation(pipeline_id)

        except Exception as e:
            logger.error(f"Stage progression failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    def _determine_next_stage(self, context: InsightContext) -> Optional[InsightState]:
        """Determine next processing stage"""
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
            final_results = self._aggregate_results(context)
            context.state = InsightState.COMPLETION
            context.completed_at = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_GENERATE_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'results': final_results,
                        'context': context.to_dict()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="control_point_manager"
                    )
                )
            )

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
                    context.completed_at - context.created_at
            ).total_seconds() if context.completed_at else None
        }

    async def _handle_error(self, pipeline_id: str, error: str) -> None:
        """Handle errors in insight processing"""
        try:
            context = self.active_contexts.get(pipeline_id)
            if context:
                context.state = InsightState.ERROR
                context.error = error
                context.updated_at = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_GENERATE_FAILED,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="control_point_manager"
                    )
                )
            )

            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    # Validation and Configuration Methods
    def _validate_insight_config(self, config: Dict[str, Any]) -> bool:
        """Validate insight generation configuration"""
        try:
            # Check required fields
            required_fields = ['enabled_features', 'processing_mode']
            if not all(field in config for field in required_fields):
                return False

            # Validate processing mode
            valid_modes = ['batch', 'streaming', 'incremental']
            if config['processing_mode'] not in valid_modes:
                return False

            # Validate enabled features
            valid_features = ['patterns', 'trends', 'relationships', 'anomalies']
            if not all(feature in valid_features for feature in config['enabled_features']):
                return False

            # Validate thresholds if provided
            if thresholds := config.get('thresholds'):
                if not all(0 < threshold <= 1 for threshold in thresholds.values()):
                    return False

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False


    async def _collect_resource_metrics(self) -> Dict[str, float]:
        """Collect current resource metrics"""
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()

            return {
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'memory_rss': memory_info.rss,
                'memory_vms': memory_info.vms,
                'thread_count': process.num_threads(),
                'open_files': len(process.open_files()),
                'context_count': len(self.active_contexts)
            }
        except Exception as e:
            logger.error(f"Resource metrics collection failed: {str(e)}")
            return {}


    def _exceeds_resource_limits(self, metrics: Dict[str, float]) -> bool:
        """Check if resource metrics exceed limits"""
        try:
            # Define resource limits
            limits = {
                'cpu_percent': 90,  # 90% CPU usage
                'memory_percent': 85,  # 85% memory usage
                'thread_count': 100,  # Maximum threads
                'context_count': 50  # Maximum active contexts
            }

            # Check each metric against its limit
            for metric_name, limit in limits.items():
                if metrics.get(metric_name, 0) > limit:
                    return True

            return False

        except Exception as e:
            logger.error(f"Resource limit check failed: {str(e)}")
            return True  # Conservative approach


    async def _handle_resource_violation(self, pipeline_id: str, metrics: Dict[str, float]) -> None:
        """Handle resource limit violations"""
        try:
            # Log violation
            logger.warning(f"Resource limits exceeded for pipeline {pipeline_id}: {metrics}")

            # Notify about resource violation
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_RESOURCE_EXCEEDED,
                    content={
                        'pipeline_id': pipeline_id,
                        'metrics': metrics,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="resource_manager"
                    )
                )
            )

            # Take corrective action
            context = self.active_contexts.get(pipeline_id)
            if context and metrics.get('memory_percent', 0) > 95:  # Critical memory usage
                await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Resource violation handling failed: {str(e)}")


    async def _handle_backpressure(self, active_count: int) -> None:
        """Handle system backpressure"""
        try:
            # Calculate pressure level
            pressure_level = min(active_count / 10, 1.0)  # Normalize to [0,1]

            # Notify about backpressure
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_BACKPRESSURE_NOTIFY,
                    content={
                        'pressure_level': pressure_level,
                        'active_count': active_count,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="control_point_manager"
                    )
                )
            )

            # Apply backpressure measures
            if pressure_level > 0.8:
                await self._pause_new_processes()

        except Exception as e:
            logger.error(f"Backpressure handling failed: {str(e)}")


    async def _pause_new_processes(self) -> None:
        """Pause accepting new processes"""
        try:
            self.state = ManagerState.BACKPRESSURE

            # Notify about paused state
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_STATE_UPDATE,
                    content={
                        'state': 'paused',
                        'reason': 'backpressure',
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="control_point_manager"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Process pausing failed: {str(e)}")


    async def _cleanup_process(self, pipeline_id: str) -> None:
        """Cleanup process resources"""
        try:
            # Get context
            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Release resources
            if context.resource_allocation:
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.INSIGHT_RESOURCE_RELEASE,
                        content={
                            'pipeline_id': pipeline_id,
                            'resources': context.resource_allocation,
                            'timestamp': datetime.now().isoformat()
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component="resource_manager"
                        )
                    )
                )

            # Clean up context
            self.active_contexts.pop(pipeline_id, None)
            self.process_timeouts.pop(pipeline_id, None)

            logger.info(f"Cleaned up resources for pipeline {pipeline_id}")

        except Exception as e:
            logger.error(f"Process cleanup failed: {str(e)}")


    def _check_metric_thresholds(self, metrics: InsightMetrics) -> bool:
        """Check if metrics exceed defined thresholds"""
        try:
            return any([
                metrics.detection_accuracy < self.insight_thresholds.get('minimum_accuracy', 0.7),
                metrics.processing_time > self.insight_thresholds.get('maximum_processing_time', 3600),
                metrics.error_rate > 0.2
            ])
        except Exception as e:
            logger.error(f"Metric threshold check failed: {str(e)}")
            return True  # Conservative approach

    async def _handle_detection_start(self, message: ProcessingMessage) -> None:
        """Handle detection process start"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            context.state = InsightState.DETECTION_IN_PROGRESS
            context.updated_at = datetime.now()

        except Exception as e:
            logger.error(f"Detection start failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_detection_progress(self, message: ProcessingMessage) -> None:
        """Handle detection progress updates"""
        pipeline_id = message.content.get('pipeline_id')
        progress = message.content.get('progress', 0)
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            context.progress = progress
            context.updated_at = datetime.now()

        except Exception as e:
            logger.error(f"Detection progress update failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_detection_complete(self, message: ProcessingMessage) -> None:
        """Handle detection process completion"""
        pipeline_id = message.content.get('pipeline_id')
        detection_results = message.content.get('results', {})
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            context.detection_results = detection_results
            context.updated_at = datetime.now()
            await self._proceed_to_next_stage(pipeline_id, detection_results)
        except Exception as e:
            logger.error(f"Detection completion failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_validate_request(self, message: ProcessingMessage) -> None:
        """Handle validation request"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            context.state = InsightState.VALIDATION_IN_PROGRESS
            context.updated_at = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_VALIDATION_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'results': context.detection_results,
                        'validation_config': context.config.get('validation_config', {})
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="insight_service"
                    )
                )
            )
        except Exception as e:
            logger.error(f"Validation request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_validate_complete(self, message: ProcessingMessage) -> None:
        """Handle validation completion"""
        pipeline_id = message.content.get('pipeline_id')
        validation_results = message.content.get('results', {})
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            context.validation_results = validation_results
            context.updated_at = datetime.now()
            await self._proceed_to_next_stage(pipeline_id, validation_results)
        except Exception as e:
            logger.error(f"Validation completion failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_validate_failed(self, message: ProcessingMessage) -> None:
        """Handle validation failure"""
        pipeline_id = message.content.get('pipeline_id')
        error = message.content.get('error', 'Validation failed')
        await self._handle_error(pipeline_id, error)

    async def _handle_health_check(self, message: ProcessingMessage) -> None:
        """Handle health check request"""
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
                'error_count': len(getattr(context, 'errors', [])),
                'processing_progress': getattr(context, 'progress', 0)
            }

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_HEALTH_STATUS,
                    content={
                        'pipeline_id': pipeline_id,
                        'health_metrics': health_metrics,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="monitoring_service"
                    )
                )
            )
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_config_update(self, message: ProcessingMessage) -> None:
        """Handle configuration update request"""
        config_updates = message.content.get('config', {})

        try:
            # Update thresholds if provided
            if thresholds := config_updates.get('thresholds'):
                self.insight_thresholds.update(thresholds)

            # Notify update completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_CONFIG_UPDATE_COMPLETE,
                    content={
                        'status': 'completed',
                        'updates': config_updates,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="control_point_manager"
                    )
                )
            )
        except Exception as e:
            logger.error(f"Config update failed: {str(e)}")
            # Optional: Handle config update failure
            await self._handle_error(None, str(e))

    async def _handle_metric_threshold_breach(self, pipeline_id: str, metrics: InsightMetrics) -> None:
        """Handle metrics threshold breach"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_METRIC_ALERT,
                    content={
                        'pipeline_id': pipeline_id,
                        'metrics': metrics.__dict__,
                        'thresholds': self.insight_thresholds,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="monitoring_service"
                    )
                )
            )  # Added missing closing parenthesis
        except Exception as e:
            logger.error(f"Metric threshold breach handling failed: {str(e)}")
            # Optional: Add more robust error handling
            try:
                # Fallback logging mechanism
                logging.getLogger('critical_errors').error(
                    f"Failed to publish metric threshold breach: {str(e)}",
                    extra={
                        'pipeline_id': pipeline_id,
                        'metrics': str(metrics),
                    }
                )
            except Exception:
                # Ensure absolute last-resort error logging
                print(f"Critical error in metric threshold breach handling: {e}")

    # Process Handler Methods
    async def _process_trends(self, trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and validate trends"""
        processed_trends = []

        for trend in trends:
            if self._validate_trend(trend):
                processed_trends.append({
                    **trend,
                    'validated': True,
                    'significance': await self._calculate_trend_significance(trend)
                })

        return processed_trends

    def _validate_trend(self, trend: Dict[str, Any]) -> bool:
        """Validate trend data"""
        try:
            # Check required fields
            required_fields = ['type', 'direction', 'strength', 'duration']
            if not all(field in trend for field in required_fields):
                return False

            # Validate trend values
            if trend['strength'] < self.insight_thresholds['minimum_correlation']:
                return False

            if trend['duration'] < 2:  # Minimum 2 time periods
                return False

            return True

        except Exception as e:
            logger.error(f"Trend validation failed: {str(e)}")
            return False

    async def _calculate_trend_significance(self, trend: Dict[str, Any]) -> float:
        """Calculate trend significance score"""
        try:
            base_strength = trend.get('strength', 0)
            duration_weight = min(trend.get('duration', 0) / 10, 1.0)  # Normalize duration
            consistency = trend.get('consistency', 0.5)

            return min(base_strength * duration_weight * consistency, 1.0)

        except Exception as e:
            logger.error(f"Trend significance calculation failed: {str(e)}")
            return 0.0

    async def _handle_generate_start(self, message: ProcessingMessage) -> None:
        """Handle start of insight generation"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            context.state = InsightState.STARTED
            context.updated_at = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_DETECTION_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'context': context.to_dict()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="insight_service"
                    )
                )
            )
        except Exception as e:
            logger.error(f"Generation start failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_generate_progress(self, message: ProcessingMessage) -> None:
        """Handle generation progress updates"""
        pipeline_id = message.content.get('pipeline_id')
        progress = message.content.get('progress', 0)
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            context.progress = progress
            context.updated_at = datetime.now()

        except Exception as e:
            logger.error(f"Progress update failed: {str(e)}")
            # Add a return statement to handle the error
            return

    async def _handle_generate_failed(self, message: ProcessingMessage) -> None:
        """Handle generation failure"""
        pipeline_id = message.content.get('pipeline_id')
        error = message.content.get('error', 'Unknown error')
        await self._handle_error(pipeline_id, error)

    async def _handle_context_analysis_request(self, message: ProcessingMessage) -> None:
        """Handle context analysis request"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            context.state = InsightState.CONTEXT_ANALYSIS
            context.updated_at = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_CONTEXT_ANALYZE_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'context': context.to_dict()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="insight_service"
                    )
                )
            )
        except Exception as e:
            logger.error(f"Context analysis request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_context_analysis_complete(self, message: ProcessingMessage) -> None:
        """Handle context analysis completion"""
        pipeline_id = message.content.get('pipeline_id')
        analysis_results = message.content.get('results', {})
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            context.state = InsightState.DETECTION_PREPARATION
            context.context_analysis_results = analysis_results
            context.updated_at = datetime.now()

            await self._proceed_to_next_stage(pipeline_id, analysis_results)

        except Exception as e:
            logger.error(f"Context analysis completion failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_resource_request(self, message: ProcessingMessage) -> None:
        """Handle resource request"""
        pipeline_id = message.content.get('pipeline_id')
        resource_config = message.content.get('resource_config', {})
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            # Check resource availability
            if not await self._check_resource_availability(resource_config):
                await self._handle_resource_unavailable(pipeline_id, 'Requested resources not available')
                return

            # Allocate resources
            context.resource_allocation.update(resource_config)
            context.updated_at = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_RESOURCE_ALLOCATED,
                    content={
                        'pipeline_id': pipeline_id,
                        'allocated_resources': resource_config,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="resource_manager"
                    )
                )
            )
        except Exception as e:
            logger.error(f"Resource request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _check_resource_availability(self, resource_config: Dict[str, Any]) -> bool:
        """Check if requested resources are available"""
        try:
            current_metrics = await self._collect_resource_metrics()

            # Define resource limits considering current usage
            available_resources = {
                'cpu': 100 - current_metrics.get('cpu_percent', 0),
                'memory': 100 - current_metrics.get('memory_percent', 0),
                'threads': 200 - current_metrics.get('thread_count', 0)
            }

            # Check if requested resources are within available limits
            for resource, requested in resource_config.items():
                if resource in available_resources:
                    if requested > available_resources[resource]:
                        return False

            return True

        except Exception as e:
            logger.error(f"Resource availability check failed: {str(e)}")
            return False

    async def _handle_resource_release(self, message: ProcessingMessage) -> None:
        """Handle resource release request"""
        pipeline_id = message.content.get('pipeline_id')
        resources = message.content.get('resources', {})
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            # Release specified resources
            for resource in resources:
                context.resource_allocation.pop(resource, None)

            context.updated_at = datetime.now()

            # Notify resource release
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_RESOURCE_RELEASED,
                    content={
                        'pipeline_id': pipeline_id,
                        'released_resources': resources,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="resource_manager"
                    )
                )
            )
        except Exception as e:
            logger.error(f"Resource release failed: {str(e)}")


    async def _handle_resource_unavailable(self, pipeline_id: str, reason: str) -> None:
        """Handle resource unavailability"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_RESOURCE_UNAVAILABLE,
                    content={
                        'pipeline_id': pipeline_id,
                        'reason': reason,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="control_point_manager"
                    )
                )
            )
            await self._handle_error(pipeline_id, f"Resource unavailable: {reason}")
        except Exception as e:
            logger.error(f"Resource unavailability handling failed: {str(e)}")


    async def _handle_backpressure_notify(self, message: ProcessingMessage) -> None:
        """Handle backpressure notification"""
        pressure_level = message.content.get('pressure_level', 0)
        try:
            if pressure_level > 0.8:  # 80% threshold
                await self._pause_new_processes()
        except Exception as e:
            logger.error(f"Backpressure handling failed: {str(e)}")


    async def _handle_relationship_process(self, message: ProcessingMessage) -> None:
        """Handle relationship analysis process"""
        pipeline_id = message.content.get('pipeline_id')
        relationships = message.content.get('relationships', [])
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            # Process and validate relationships
            validated_relationships = await self._process_relationships(relationships)

            # Update context
            context.intermediate_results['relationships'] = validated_relationships
            context.updated_at = datetime.now()

            # Proceed to next stage
            await self._proceed_to_next_stage(pipeline_id, validated_relationships)
        except Exception as e:
            logger.error(f"Relationship processing failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_anomaly_process(self, message: ProcessingMessage) -> None:
        """Handle anomaly detection process"""
        pipeline_id = message.content.get('pipeline_id')
        anomalies = message.content.get('anomalies', [])
        context = self.active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            # Process and validate anomalies
            validated_anomalies = await self._process_anomalies(anomalies)

            # Update context
            context.intermediate_results['anomalies'] = validated_anomalies
            context.updated_at = datetime.now()

            # Proceed to next stage
            await self._proceed_to_next_stage(pipeline_id, validated_anomalies)
        except Exception as e:
            logger.error(f"Anomaly processing failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _process_relationships(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and validate relationships"""
        validated_relationships = []
        for relationship in relationships:
            if await self._validate_relationship(relationship):
                validated_relationships.append({
                    **relationship,
                    'validated': True,
                    'strength': await self._calculate_relationship_strength(relationship)
                })
        return validated_relationships


    async def _process_anomalies(self, anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and validate anomalies"""
        validated_anomalies = []
        for anomaly in anomalies:
            if await self._validate_anomaly(anomaly):
                validated_anomalies.append({
                    **anomaly,
                    'validated': True,
                    'severity': await self._calculate_anomaly_severity(anomaly)
                })
        return validated_anomalies


    async def _validate_relationship(self, relationship: Dict[str, Any]) -> bool:
        """Validate relationship data"""
        try:
            required_fields = ['source', 'target', 'type', 'strength']
            if not all(field in relationship for field in required_fields):
                return False

            if relationship['strength'] < self.insight_thresholds['minimum_correlation']:
                return False

            return True
        except Exception as e:
            logger.error(f"Relationship validation failed: {str(e)}")
            return False


    async def _validate_anomaly(self, anomaly: Dict[str, Any]) -> bool:
        """Validate anomaly data"""
        try:
            required_fields = ['type', 'score', 'confidence']
            if not all(field in anomaly for field in required_fields):
                return False

            if anomaly['confidence'] < self.insight_thresholds['confidence_threshold']:
                return False

            return True
        except Exception as e:
            logger.error(f"Anomaly validation failed: {str(e)}")
            return False


    async def _calculate_relationship_strength(self, relationship: Dict[str, Any]) -> float:
        """Calculate relationship strength score"""
        try:
            base_strength = relationship.get('strength', 0)
            support = relationship.get('support', 0.5)
            confidence = relationship.get('confidence', 0.5)

            return min(base_strength * support * confidence, 1.0)
        except Exception as e:
            logger.error(f"Relationship strength calculation failed: {str(e)}")
            return 0.0

    async def _handle_generate_complete(self, message: ProcessingMessage) -> None:
        """Handle complete insight generation process"""
        pipeline_id = message.content.get('pipeline_id')
        final_results = message.content.get('results', {})
        context = self.active_contexts.get(pipeline_id)

        if not context:
            logger.warning(f"No context found for pipeline {pipeline_id} during generate complete")
            return

        try:
            context.state = InsightState.COMPLETION
            context.completed_at = datetime.now()
            context.final_results = final_results

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_PROCESSING_FINALIZED,
                    content={
                        'pipeline_id': pipeline_id,
                        'results': final_results,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="control_point_manager"
                    )
                )
            )

            # Optional cleanup
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Generate complete process failed for pipeline {pipeline_id}: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_pattern_process(self, message: ProcessingMessage) -> None:
        """Handle pattern processing for insights"""
        pipeline_id = message.content.get('pipeline_id')
        patterns = message.content.get('patterns', [])
        context = self.active_contexts.get(pipeline_id)

        if not context:
            logger.warning(f"No context found for pipeline {pipeline_id} during pattern processing")
            return

        try:
            # Process and validate patterns
            processed_patterns = await self._process_patterns(patterns)

            # Update context
            context.intermediate_results['patterns'] = processed_patterns
            context.updated_at = datetime.now()

            # Proceed to next stage
            await self._proceed_to_next_stage(pipeline_id, processed_patterns)

        except Exception as e:
            logger.error(f"Pattern processing failed for pipeline {pipeline_id}: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_trend_process(self, message: ProcessingMessage) -> None:
        """Handle trend processing for insights"""
        pipeline_id = message.content.get('pipeline_id')
        trends = message.content.get('trends', [])
        context = self.active_contexts.get(pipeline_id)

        if not context:
            logger.warning(f"No context found for pipeline {pipeline_id} during trend processing")
            return

        try:
            # Process and validate trends
            processed_trends = await self._process_trends(trends)

            # Update context
            context.intermediate_results['trends'] = processed_trends
            context.updated_at = datetime.now()

            # Proceed to next stage
            await self._proceed_to_next_stage(pipeline_id, processed_trends)

        except Exception as e:
            logger.error(f"Trend processing failed for pipeline {pipeline_id}: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_metrics_update(self, message: ProcessingMessage) -> None:
        """Handle metrics update for insights"""
        pipeline_id = message.content.get('pipeline_id')
        metrics = message.content.get('metrics')
        context = self.active_contexts.get(pipeline_id)

        if not context:
            logger.warning(f"No context found for pipeline {pipeline_id} during metrics update")
            return

        try:
            # Update context metrics
            context.metrics = metrics
            context.updated_at = datetime.now()

            # Check if metrics breach any thresholds
            if self._check_metric_thresholds(metrics):
                await self._handle_metric_threshold_breach(pipeline_id, metrics)

            # Optional: Publish metrics update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_METRICS_UPDATED,
                    content={
                        'pipeline_id': pipeline_id,
                        'metrics': metrics.__dict__,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="monitoring_service"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Metrics update failed for pipeline {pipeline_id}: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _calculate_anomaly_severity(self, anomaly: Dict[str, Any]) -> float:
        """Calculate anomaly severity score"""
        try:
            base_score = anomaly.get('score', 0)
            confidence = anomaly.get('confidence', 0.5)
            impact = anomaly.get('impact', 0.5)

            return min(base_score * confidence * impact, 1.0)
        except Exception as e:
            logger.error(f"Anomaly severity calculation failed: {str(e)}")
            return 0.0