import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller
from scipy import stats

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

        # New attributes for the new implementation
        self.active_insights: Dict[str, Dict[str, Any]] = {}
        self.insight_metrics: Dict[str, Dict[str, float]] = {}
        self.config = {
            "max_retries": 3,
            "timeout_seconds": 300,
            "batch_size": 1000,
            "max_concurrent_insights": 5,
            "pattern_detection": {
                "min_pattern_length": 3,
                "max_pattern_length": 10,
                "similarity_threshold": 0.8
            },
            "trend_analysis": {
                "window_size": 30,
                "min_trend_length": 5,
                "significance_level": 0.05
            },
            "anomaly_detection": {
                "contamination": 0.1,
                "random_state": 42
            },
            "correlation_analysis": {
                "min_correlation": 0.3
            },
            "seasonality_analysis": {
                "default_period": 12
            }
        }

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

    async def _initialize_manager(self):
        """Initialize the insight manager"""
        self._setup_message_handlers()
        self.logger.info("Insight Manager initialized")

    def _setup_message_handlers(self):
        """Set up message handlers for the manager"""
        self.message_handlers = {
            MessageType.INSIGHT_REQUEST: self._handle_insight_request,
            MessageType.INSIGHT_START: self._handle_insight_start,
            MessageType.INSIGHT_PROGRESS: self._handle_insight_progress,
            MessageType.INSIGHT_COMPLETE: self._handle_insight_complete,
            MessageType.INSIGHT_FAILED: self._handle_insight_failed
        }

    async def _handle_insight_request(self, message: ProcessingMessage) -> ProcessingMessage:
        """Handle insight request message"""
        try:
            content = message.content
            insight_id = content.get("insight_id")
            data = pd.DataFrame(content.get("data", {}))
            insight_types = content.get("insight_types", ["pattern", "trend", "anomaly"])
            
            if not self._validate_insight_request(content):
                return ProcessingMessage(
                    message_type=MessageType.INSIGHT_FAILED,
                    content={
                        "insight_id": insight_id,
                        "error": "Invalid insight request",
                        "timestamp": datetime.now().isoformat()
                    }
                )

            # Create insight context
            insight_context = {
                "insight_id": insight_id,
                "data": data,
                "insight_types": insight_types,
                "start_time": datetime.now(),
                "status": "pending"
            }

            # Store insight context
            self.active_insights[insight_id] = insight_context

            # Start insight generation
            await self._start_insight_generation(insight_id)

            return ProcessingMessage(
                message_type=MessageType.INSIGHT_START,
                content={
                    "insight_id": insight_id,
                    "status": "started",
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            self.logger.error(f"Error handling insight request: {str(e)}")
            return ProcessingMessage(
                message_type=MessageType.INSIGHT_FAILED,
                content={
                    "insight_id": content.get("insight_id"),
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _start_insight_generation(self, insight_id: str):
        """Start the insight generation process"""
        try:
            insight_context = self.active_insights[insight_id]
            data = insight_context["data"]
            insight_types = insight_context["insight_types"]
            insights = {}

            # Generate requested insights
            if "pattern" in insight_types:
                insights["patterns"] = await self._detect_patterns(data)
            if "trend" in insight_types:
                insights["trends"] = await self._analyze_trends(data)
            if "anomaly" in insight_types:
                insights["anomalies"] = await self._detect_anomalies(data)
            if "correlation" in insight_types:
                insights["correlations"] = await self._analyze_correlations(data)
            if "seasonality" in insight_types:
                insights["seasonality"] = await self._analyze_seasonality(data)

            # Update insight context
            insight_context["insights"] = insights
            insight_context["status"] = "completed"
            insight_context["end_time"] = datetime.now()

            # Update metrics
            await self._update_insight_metrics(insight_id)

            # Publish completion message
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_COMPLETE,
                    content={
                        "insight_id": insight_id,
                        "insights": insights,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            )

        except Exception as e:
            self.logger.error(f"Error in insight generation: {str(e)}")
            insight_context["status"] = "failed"
            insight_context["error"] = str(e)
            insight_context["end_time"] = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_FAILED,
                    content={
                        "insight_id": insight_id,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                )
            )

    async def _detect_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detect patterns in the data"""
        try:
            patterns = {}
            
            # Prepare data
            numeric_data = data.select_dtypes(include=[np.number])
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(numeric_data)

            # Apply PCA for dimensionality reduction
            pca = PCA(n_components=2)
            pca_data = pca.fit_transform(scaled_data)

            # Detect patterns using DBSCAN
            dbscan = DBSCAN(
                eps=0.5,
                min_samples=self.config["pattern_detection"]["min_pattern_length"]
            )
            cluster_labels = dbscan.fit_predict(pca_data)

            # Analyze patterns
            unique_clusters = np.unique(cluster_labels[cluster_labels != -1])
            for cluster in unique_clusters:
                cluster_points = pca_data[cluster_labels == cluster]
                pattern = {
                    "size": len(cluster_points),
                    "center": cluster_points.mean(axis=0).tolist(),
                    "spread": cluster_points.std(axis=0).tolist(),
                    "points": cluster_points.tolist(),
                    "density": self._calculate_pattern_density(cluster_points),
                    "stability": self._calculate_pattern_stability(cluster_points),
                    "coherence": self._calculate_pattern_coherence(cluster_points)
                }
                patterns[f"pattern_{cluster}"] = pattern

            return {
                "patterns": patterns,
                "pattern_count": len(patterns),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error detecting patterns: {str(e)}")
            raise

    def _calculate_pattern_density(self, points: np.ndarray) -> float:
        """Calculate pattern density"""
        try:
            # Calculate pairwise distances
            distances = np.linalg.norm(points[:, np.newaxis] - points, axis=2)
            # Calculate average distance
            avg_distance = np.mean(distances)
            # Normalize density (closer points = higher density)
            return 1 / (1 + avg_distance)
        except Exception as e:
            self.logger.error(f"Error calculating pattern density: {str(e)}")
            return 0.0

    def _calculate_pattern_stability(self, points: np.ndarray) -> float:
        """Calculate pattern stability"""
        try:
            # Calculate variance in each dimension
            variances = np.var(points, axis=0)
            # Normalize stability (lower variance = higher stability)
            return 1 / (1 + np.mean(variances))
        except Exception as e:
            self.logger.error(f"Error calculating pattern stability: {str(e)}")
            return 0.0

    def _calculate_pattern_coherence(self, points: np.ndarray) -> float:
        """Calculate pattern coherence"""
        try:
            # Calculate correlation between dimensions
            correlations = np.corrcoef(points.T)
            # Calculate average correlation
            avg_correlation = np.mean(np.abs(correlations))
            return avg_correlation
        except Exception as e:
            self.logger.error(f"Error calculating pattern coherence: {str(e)}")
            return 0.0

    async def _analyze_trends(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze trends in the data"""
        try:
            trends = {}
            
            # Analyze each numeric column
            for column in data.select_dtypes(include=[np.number]).columns:
                # Perform seasonal decomposition
                decomposition = seasonal_decompose(
                    data[column],
                    period=self.config["trend_analysis"]["window_size"]
                )

                # Perform stationarity test
                _, p_value = adfuller(data[column])

                # Calculate trend strength
                trend_strength = self._calculate_trend_strength(decomposition.trend)
                
                # Calculate seasonality strength
                seasonality_strength = self._calculate_seasonality_strength(decomposition.seasonal)
                
                # Calculate trend acceleration
                acceleration = self._calculate_trend_acceleration(decomposition.trend)

                trend = {
                    "direction": "increasing" if decomposition.trend.iloc[-1] > decomposition.trend.iloc[0] else "decreasing",
                    "magnitude": abs(decomposition.trend.iloc[-1] - decomposition.trend.iloc[0]),
                    "stationarity": "stationary" if p_value < self.config["trend_analysis"]["significance_level"] else "non-stationary",
                    "seasonality": bool(decomposition.seasonal.any()),
                    "residuals": decomposition.resid.tolist(),
                    "trend_strength": trend_strength,
                    "seasonality_strength": seasonality_strength,
                    "acceleration": acceleration,
                    "volatility": self._calculate_volatility(decomposition.resid)
                }
                trends[column] = trend

            return {
                "trends": trends,
                "trend_count": len(trends),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error analyzing trends: {str(e)}")
            raise

    def _calculate_trend_strength(self, trend: pd.Series) -> float:
        """Calculate trend strength"""
        try:
            # Calculate R-squared of linear fit
            x = np.arange(len(trend))
            slope, intercept = np.polyfit(x, trend, 1)
            y_pred = slope * x + intercept
            r_squared = 1 - np.sum((trend - y_pred) ** 2) / np.sum((trend - np.mean(trend)) ** 2)
            return max(0, min(1, r_squared))
        except Exception as e:
            self.logger.error(f"Error calculating trend strength: {str(e)}")
            return 0.0

    def _calculate_seasonality_strength(self, seasonal: pd.Series) -> float:
        """Calculate seasonality strength"""
        try:
            # Calculate ratio of seasonal to total variation
            seasonal_var = np.var(seasonal)
            total_var = np.var(seasonal + seasonal.mean())
            return seasonal_var / total_var if total_var > 0 else 0
        except Exception as e:
            self.logger.error(f"Error calculating seasonality strength: {str(e)}")
            return 0.0

    def _calculate_trend_acceleration(self, trend: pd.Series) -> float:
        """Calculate trend acceleration"""
        try:
            # Calculate second derivative
            x = np.arange(len(trend))
            coeffs = np.polyfit(x, trend, 2)
            return coeffs[0]  # Second derivative coefficient
        except Exception as e:
            self.logger.error(f"Error calculating trend acceleration: {str(e)}")
            return 0.0

    def _calculate_volatility(self, residuals: pd.Series) -> float:
        """Calculate volatility"""
        try:
            # Calculate rolling standard deviation
            rolling_std = residuals.rolling(window=20).std()
            return np.mean(rolling_std) / np.std(residuals) if np.std(residuals) > 0 else 0
        except Exception as e:
            self.logger.error(f"Error calculating volatility: {str(e)}")
            return 0.0

    async def _detect_anomalies(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detect anomalies in the data"""
        try:
            anomalies = {}
            
            # Prepare data
            numeric_data = data.select_dtypes(include=[np.number])
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(numeric_data)

            # Detect anomalies using Isolation Forest
            iso_forest = IsolationForest(
                contamination=self.config["anomaly_detection"]["contamination"],
                random_state=self.config["anomaly_detection"]["random_state"]
            )
            anomaly_labels = iso_forest.fit_predict(scaled_data)

            # Analyze anomalies
            anomaly_indices = np.where(anomaly_labels == -1)[0]
            for idx in anomaly_indices:
                # Calculate anomaly impact
                impact = self._calculate_anomaly_impact(numeric_data, idx)
                
                # Calculate anomaly persistence
                persistence = self._calculate_anomaly_persistence(numeric_data, idx)
                
                # Calculate anomaly context
                context = self._calculate_anomaly_context(numeric_data, idx)

                anomaly = {
                    "index": int(idx),
                    "values": numeric_data.iloc[idx].to_dict(),
                    "score": float(iso_forest.score_samples([scaled_data[idx]])[0]),
                    "impact": impact,
                    "persistence": persistence,
                    "context": context,
                    "severity": self._calculate_anomaly_severity(impact, persistence, context)
                }
                anomalies[f"anomaly_{idx}"] = anomaly

            return {
                "anomalies": anomalies,
                "anomaly_count": len(anomalies),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {str(e)}")
            raise

    def _calculate_anomaly_impact(self, data: pd.DataFrame, index: int) -> float:
        """Calculate anomaly impact"""
        try:
            # Calculate deviation from mean
            mean_values = data.mean()
            std_values = data.std()
            deviations = np.abs(data.iloc[index] - mean_values) / std_values
            return np.mean(deviations)
        except Exception as e:
            self.logger.error(f"Error calculating anomaly impact: {str(e)}")
            return 0.0

    def _calculate_anomaly_persistence(self, data: pd.DataFrame, index: int) -> float:
        """Calculate anomaly persistence"""
        try:
            # Look at surrounding values
            window = 5
            start_idx = max(0, index - window)
            end_idx = min(len(data), index + window + 1)
            surrounding_values = data.iloc[start_idx:end_idx]
            
            # Calculate how long the anomaly persists
            persistence = 0
            for i in range(window):
                if index + i < len(data):
                    if self._is_anomaly(data.iloc[index + i]):
                        persistence += 1
                if index - i >= 0:
                    if self._is_anomaly(data.iloc[index - i]):
                        persistence += 1
            
            return persistence / (2 * window)
        except Exception as e:
            self.logger.error(f"Error calculating anomaly persistence: {str(e)}")
            return 0.0

    def _calculate_anomaly_context(self, data: pd.DataFrame, index: int) -> Dict[str, float]:
        """Calculate anomaly context"""
        try:
            # Calculate various context metrics
            context = {
                "local_density": self._calculate_local_density(data, index),
                "global_density": self._calculate_global_density(data),
                "isolation": self._calculate_isolation(data, index),
                "neighborhood_consistency": self._calculate_neighborhood_consistency(data, index)
            }
            return context
        except Exception as e:
            self.logger.error(f"Error calculating anomaly context: {str(e)}")
            return {}

    def _calculate_anomaly_severity(self, impact: float, persistence: float, context: Dict[str, float]) -> float:
        """Calculate anomaly severity"""
        try:
            # Combine various factors into severity score
            severity = (
                0.4 * impact +
                0.3 * persistence +
                0.3 * (context.get("isolation", 0) * 0.5 + context.get("neighborhood_consistency", 0) * 0.5)
            )
            return min(1.0, max(0.0, severity))
        except Exception as e:
            self.logger.error(f"Error calculating anomaly severity: {str(e)}")
            return 0.0

    def _is_anomaly(self, values: pd.Series) -> bool:
        """Check if values are anomalous"""
        try:
            # Simple threshold-based anomaly detection
            mean = values.mean()
            std = values.std()
            return any(np.abs(values - mean) > 3 * std)
        except Exception as e:
            self.logger.error(f"Error checking for anomaly: {str(e)}")
            return False

    def _calculate_local_density(self, data: pd.DataFrame, index: int) -> float:
        """Calculate local density around anomaly"""
        try:
            window = 10
            start_idx = max(0, index - window)
            end_idx = min(len(data), index + window + 1)
            local_data = data.iloc[start_idx:end_idx]
            return len(local_data) / (2 * window)
        except Exception as e:
            self.logger.error(f"Error calculating local density: {str(e)}")
            return 0.0

    def _calculate_global_density(self, data: pd.DataFrame) -> float:
        """Calculate global data density"""
        try:
            return len(data) / (data.max() - data.min()).sum()
        except Exception as e:
            self.logger.error(f"Error calculating global density: {str(e)}")
            return 0.0

    def _calculate_isolation(self, data: pd.DataFrame, index: int) -> float:
        """Calculate isolation score"""
        try:
            # Calculate distance to nearest neighbors
            distances = np.linalg.norm(data - data.iloc[index], axis=1)
            distances = distances[distances > 0]  # Remove self-distance
            return np.mean(distances[:5]) / np.mean(distances) if len(distances) > 0 else 0
        except Exception as e:
            self.logger.error(f"Error calculating isolation: {str(e)}")
            return 0.0

    def _calculate_neighborhood_consistency(self, data: pd.DataFrame, index: int) -> float:
        """Calculate neighborhood consistency"""
        try:
            window = 5
            start_idx = max(0, index - window)
            end_idx = min(len(data), index + window + 1)
            neighborhood = data.iloc[start_idx:end_idx]
            
            # Calculate variance in neighborhood
            variances = np.var(neighborhood, axis=0)
            return 1 / (1 + np.mean(variances))
        except Exception as e:
            self.logger.error(f"Error calculating neighborhood consistency: {str(e)}")
            return 0.0

    def _validate_insight_request(self, content: Dict[str, Any]) -> bool:
        """Validate insight request content"""
        required_fields = ["insight_id", "data", "insight_types"]
        return all(field in content for field in required_fields)

    async def _update_insight_metrics(self, insight_id: str):
        """Update insight metrics"""
        try:
            insight_context = self.active_insights[insight_id]
            start_time = insight_context["start_time"]
            end_time = insight_context["end_time"]
            duration = (end_time - start_time).total_seconds()

            self.insight_metrics[insight_id] = {
                "duration": duration,
                "status": insight_context["status"],
                "insight_types": insight_context["insight_types"],
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error updating insight metrics: {str(e)}")

    async def _cleanup_resources(self):
        """Clean up manager resources"""
        self.active_insights.clear()
        self.insight_metrics.clear()
        self.logger.info("Insight Manager resources cleaned up")

    async def _analyze_correlations(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze correlations between variables"""
        try:
            correlations = {}
            
            # Prepare numeric data
            numeric_data = data.select_dtypes(include=[np.number])
            
            # Calculate correlation matrix
            corr_matrix = numeric_data.corr()
            
            # Find significant correlations
            significant_correlations = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    correlation = corr_matrix.iloc[i, j]
                    if abs(correlation) >= self.config.get("correlation_analysis", {}).get("min_correlation", 0.3):
                        # Calculate correlation strength and significance
                        strength = self._calculate_correlation_strength(correlation)
                        significance = self._calculate_correlation_significance(
                            numeric_data[corr_matrix.columns[i]],
                            numeric_data[corr_matrix.columns[j]]
                        )
                        
                        # Calculate correlation stability
                        stability = self._calculate_correlation_stability(
                            numeric_data[corr_matrix.columns[i]],
                            numeric_data[corr_matrix.columns[j]]
                        )
                        
                        # Calculate correlation direction
                        direction = self._determine_correlation_direction(correlation)
                        
                        significant_correlations.append({
                            "variable1": corr_matrix.columns[i],
                            "variable2": corr_matrix.columns[j],
                            "correlation": float(correlation),
                            "strength": strength,
                            "significance": significance,
                            "stability": stability,
                            "direction": direction,
                            "type": self._determine_correlation_type(correlation, strength)
                        })
            
            # Sort correlations by strength
            significant_correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)
            
            return {
                "correlations": significant_correlations,
                "correlation_count": len(significant_correlations),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing correlations: {str(e)}")
            raise

    def _calculate_correlation_strength(self, correlation: float) -> float:
        """Calculate correlation strength"""
        try:
            # Convert correlation to strength score (0-1)
            return min(abs(correlation), 1.0)
        except Exception as e:
            self.logger.error(f"Error calculating correlation strength: {str(e)}")
            return 0.0

    def _calculate_correlation_significance(self, var1: pd.Series, var2: pd.Series) -> float:
        """Calculate correlation significance"""
        try:
            # Use Fisher transformation for significance
            n = len(var1)
            r = var1.corr(var2)
            z = 0.5 * np.log((1 + r) / (1 - r))
            se = 1 / np.sqrt(n - 3)
            z_score = abs(z / se)
            return 1 - (2 * (1 - stats.norm.cdf(z_score)))
        except Exception as e:
            self.logger.error(f"Error calculating correlation significance: {str(e)}")
            return 0.0

    def _calculate_correlation_stability(self, var1: pd.Series, var2: pd.Series) -> float:
        """Calculate correlation stability"""
        try:
            # Calculate correlation over different time windows
            window_sizes = [10, 20, 50]
            correlations = []
            for window in window_sizes:
                rolling_corr = var1.rolling(window=window).corr(var2)
                correlations.append(rolling_corr.std())
            
            # Lower standard deviation indicates higher stability
            return 1 / (1 + np.mean(correlations))
        except Exception as e:
            self.logger.error(f"Error calculating correlation stability: {str(e)}")
            return 0.0

    def _determine_correlation_direction(self, correlation: float) -> str:
        """Determine correlation direction"""
        if correlation > 0:
            return "positive"
        elif correlation < 0:
            return "negative"
        else:
            return "none"

    def _determine_correlation_type(self, correlation: float, strength: float) -> str:
        """Determine correlation type"""
        if abs(correlation) < 0.3:
            return "weak"
        elif abs(correlation) < 0.7:
            return "moderate"
        else:
            return "strong"

    async def _analyze_seasonality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze seasonality in the data"""
        try:
            seasonality_results = {}
            
            # Analyze each numeric column
            for column in data.select_dtypes(include=[np.number]).columns:
                # Perform seasonal decomposition
                decomposition = seasonal_decompose(
                    data[column],
                    period=self.config.get("seasonality_analysis", {}).get("default_period", 12)
                )
                
                # Calculate seasonality metrics
                seasonality_metrics = {
                    "strength": self._calculate_seasonality_strength(decomposition.seasonal),
                    "period": self._detect_seasonality_period(decomposition.seasonal),
                    "consistency": self._calculate_seasonality_consistency(decomposition.seasonal),
                    "amplitude": self._calculate_seasonality_amplitude(decomposition.seasonal),
                    "phase": self._calculate_seasonality_phase(decomposition.seasonal),
                    "significance": self._calculate_seasonality_significance(decomposition.seasonal)
                }
                
                # Determine seasonality type
                seasonality_metrics["type"] = self._determine_seasonality_type(seasonality_metrics)
                
                # Store results
                seasonality_results[column] = seasonality_metrics
            
            return {
                "seasonality": seasonality_results,
                "seasonality_count": len(seasonality_results),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing seasonality: {str(e)}")
            raise

    def _detect_seasonality_period(self, seasonal: pd.Series) -> int:
        """Detect seasonality period"""
        try:
            # Use autocorrelation to detect period
            autocorr = pd.Series(seasonal).autocorr()
            if autocorr > 0.7:  # Strong autocorrelation indicates seasonality
                # Find the period with highest autocorrelation
                periods = range(2, len(seasonal) // 2)
                max_corr = 0
                best_period = 0
                for period in periods:
                    corr = seasonal.autocorr(lag=period)
                    if corr > max_corr:
                        max_corr = corr
                        best_period = period
                return best_period
            return 0
        except Exception as e:
            self.logger.error(f"Error detecting seasonality period: {str(e)}")
            return 0

    def _calculate_seasonality_consistency(self, seasonal: pd.Series) -> float:
        """Calculate seasonality consistency"""
        try:
            # Calculate how consistent the seasonal pattern is
            period = self._detect_seasonality_period(seasonal)
            if period == 0:
                return 0.0
            
            # Compare seasonal patterns across periods
            patterns = []
            for i in range(0, len(seasonal) - period, period):
                pattern = seasonal[i:i + period]
                patterns.append(pattern)
            
            if not patterns:
                return 0.0
            
            # Calculate pattern similarity
            similarities = []
            for i in range(len(patterns)):
                for j in range(i + 1, len(patterns)):
                    similarity = np.corrcoef(patterns[i], patterns[j])[0, 1]
                    similarities.append(similarity)
            
            return np.mean(similarities) if similarities else 0.0
        except Exception as e:
            self.logger.error(f"Error calculating seasonality consistency: {str(e)}")
            return 0.0

    def _calculate_seasonality_amplitude(self, seasonal: pd.Series) -> float:
        """Calculate seasonality amplitude"""
        try:
            # Calculate the magnitude of seasonal variation
            return np.std(seasonal) / np.mean(seasonal) if np.mean(seasonal) != 0 else 0
        except Exception as e:
            self.logger.error(f"Error calculating seasonality amplitude: {str(e)}")
            return 0.0

    def _calculate_seasonality_phase(self, seasonal: pd.Series) -> float:
        """Calculate seasonality phase"""
        try:
            # Calculate the phase shift of the seasonal pattern
            period = self._detect_seasonality_period(seasonal)
            if period == 0:
                return 0.0
            
            # Find the peak position in the first period
            first_period = seasonal[:period]
            peak_position = np.argmax(first_period)
            
            # Normalize phase to [0, 1]
            return peak_position / period
        except Exception as e:
            self.logger.error(f"Error calculating seasonality phase: {str(e)}")
            return 0.0

    def _calculate_seasonality_significance(self, seasonal: pd.Series) -> float:
        """Calculate seasonality significance"""
        try:
            # Calculate how significant the seasonal component is
            total_var = np.var(seasonal + seasonal.mean())
            seasonal_var = np.var(seasonal)
            return seasonal_var / total_var if total_var > 0 else 0
        except Exception as e:
            self.logger.error(f"Error calculating seasonality significance: {str(e)}")
            return 0.0

    def _determine_seasonality_type(self, metrics: Dict[str, float]) -> str:
        """Determine seasonality type based on metrics"""
        try:
            strength = metrics.get("strength", 0)
            consistency = metrics.get("consistency", 0)
            amplitude = metrics.get("amplitude", 0)
            
            if strength < 0.3 or consistency < 0.3:
                return "none"
            elif strength > 0.7 and consistency > 0.7:
                return "strong"
            elif amplitude > 0.5:
                return "moderate"
            else:
                return "weak"
        except Exception as e:
            self.logger.error(f"Error determining seasonality type: {str(e)}")
            return "unknown"