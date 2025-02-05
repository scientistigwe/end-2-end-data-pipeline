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
    MonitoringContext,
    MonitoringState,
    ComponentType,
    ModuleIdentifier
)

logger = logging.getLogger(__name__)


class MonitoringService:
    """
    Service layer for monitoring functionality.
    Handles business logic and coordinates between manager and handler.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        # Service identifier
        self.module_identifier = ModuleIdentifier(
            component_name="monitoring_service",
            component_type=ComponentType.MONITORING_SERVICE,
            department="monitoring",
            role="service"
        )

        # Active service requests
        self.active_contexts: Dict[str, MonitoringContext] = {}

        # Setup message handlers
        self._setup_message_handlers()

    async def _setup_message_handlers(self) -> None:
        """Setup handlers for service-level messages"""
        handlers = {
            # Monitoring Process Flow
            MessageType.MONITORING_PROCESS_START: self._handle_service_start,
            MessageType.MONITORING_PROCESS_FAILED: self._handle_error,
            MessageType.MONITORING_HEALTH_CHECK: self._handle_health_update,

            # Metrics Collection
            MessageType.MONITORING_METRICS_COLLECT: self._handle_metrics_collected,
            MessageType.MONITORING_METRICS_UPDATE: self._handle_metrics_update,

            # Alert Management
            MessageType.MONITORING_ALERT_GENERATE: self._handle_alert_detected,
            MessageType.MONITORING_ALERT_PROCESS: self._handle_alert_process,

            # Configuration and Control
            MessageType.MONITORING_CONFIG_UPDATE: self._handle_config_update,
            MessageType.MONITORING_PROCESS_COMPLETE: self._handle_service_stop,

            # Error and Component Communication
            MessageType.MONITORING_COMPONENT_ERROR: self._handle_component_error
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_component_error(self, message: ProcessingMessage) -> None:
        """
        Handle errors reported by a specific monitoring component

        Args:
            message (ProcessingMessage): Message containing component error details
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_contexts.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for component error in pipeline {pipeline_id}")
                return

            # Extract error details
            error_component = message.content.get('component', 'unknown')
            error_details = message.content.get('error', {})

            # Log the error
            logger.error(f"Monitoring component error: {error_details}")

            # Publish comprehensive error notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESS_FAILED,
                    content={
                        'pipeline_id': pipeline_id,
                        'component': error_component,
                        'error_details': error_details,
                        'timestamp': datetime.now().isoformat(),
                        'current_state': context.monitor_state.value
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        processing_stage=ProcessingStage.PROCESSING
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Attempt error recovery
            await self._handle_error_recovery(context, error_component, error_details)

        except Exception as e:
            logger.error(f"Component error handling failed: {str(e)}")
            await self._handle_error(message, f"Component error handling failed: {str(e)}")

    async def _handle_error_recovery(self, context: MonitoringContext, error_component: str,
                                     error_details: Dict[str, Any]) -> None:
        """
        Attempt to recover from component error

        Args:
            context (MonitoringContext): Current monitoring context
            error_component (str): Component that reported the error
            error_details (Dict[str, Any]): Error details
        """
        # Determine error severity
        error_severity = error_details.get('severity', 'medium')

        # Track error attempts
        error_count = context.retry_counts.get(error_component, 0) + 1
        context.retry_counts[error_component] = error_count

        # Recovery strategy
        if error_severity in ['low', 'medium'] and error_count <= 3:
            # Attempt to restart or recover the component
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_COMPONENT_ERROR,
                    content={
                        'pipeline_id': context.pipeline_id,
                        'component': error_component,
                        'action': 'recover',
                        'retry_count': error_count
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )
        else:
            # Critical error or max retries exceeded
            await self._handle_error(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESS_FAILED,
                    content={
                        'pipeline_id': context.pipeline_id,
                        'reason': f'Unrecoverable error in {error_component}',
                        'error_details': error_details
                    }
                ),
                f"Unrecoverable error in component {error_component}"
            )

    async def _handle_config_update(self, message: ProcessingMessage) -> None:
        """
        Handle configuration update for monitoring service

        Args:
            message (ProcessingMessage): Message containing configuration updates
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_contexts.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for config update in pipeline {pipeline_id}")
                return

            # Extract configuration updates
            config_updates = message.content.get('config', {})

            # Update context configuration
            for key, value in config_updates.items():
                # Dynamically update context attributes
                if hasattr(context, key):
                    setattr(context, key, value)

                # Handle specific configuration areas
                if key == 'metric_types':
                    context.metric_types = value
                elif key == 'collectors':
                    context.collectors_enabled = value
                elif key == 'collection_interval':
                    context.collection_interval = value

            # Publish configuration update acknowledgment
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_CONFIG_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'updated',
                        'applied_configs': list(config_updates.keys())
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

            # Trigger reconfiguration of monitoring components
            await self._apply_config_updates(context, config_updates)

        except Exception as e:
            logger.error(f"Configuration update failed: {str(e)}")
            await self._handle_error(message, f"Config update error: {str(e)}")

    async def _apply_config_updates(self, context: MonitoringContext, config_updates: Dict[str, Any]) -> None:
        """
        Apply configuration updates to monitoring components

        Args:
            context (MonitoringContext): Current monitoring context
            config_updates (Dict[str, Any]): Configuration updates to apply
        """
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.MONITORING_METRICS_UPDATE,
                content={
                    'pipeline_id': context.pipeline_id,
                    'config_updates': config_updates
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="monitoring_handler"
                )
            )
        )

    async def _handle_alert_process(self, message: ProcessingMessage) -> None:
        """
        Handle processing of detected alerts

        Args:
            message (ProcessingMessage): Message containing alert processing request
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_contexts.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for alert processing in pipeline {pipeline_id}")
                return

            # Extract alert details
            alert = message.content.get('alert', {})
            processing_action = message.content.get('action', 'default')

            # Process alert based on action
            if processing_action == 'escalate':
                await self._escalate_alert(context, alert)
            elif processing_action == 'resolve':
                await self._resolve_alert(context, alert)
            else:
                await self._default_alert_processing(context, alert)

            # Publish alert processing result
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_RESOLVE,
                    content={
                        'pipeline_id': pipeline_id,
                        'alert_id': alert.get('alert_id'),
                        'status': 'processed',
                        'action': processing_action
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Alert processing failed: {str(e)}")
            await self._handle_error(message, f"Alert processing error: {str(e)}")

    async def _default_alert_processing(self, context: MonitoringContext, alert: Dict[str, Any]) -> None:
        """
        Default alert processing method

        Args:
            context (MonitoringContext): Current monitoring context
            alert (Dict[str, Any]): Alert details
        """
        # Log the alert
        logger.info(f"Processing alert: {alert}")
        context.add_alert(alert)

    async def _escalate_alert(self, context: MonitoringContext, alert: Dict[str, Any]) -> None:
        """
        Escalate an alert to higher priority

        Args:
            context (MonitoringContext): Current monitoring context
            alert (Dict[str, Any]): Alert details
        """
        # Publish escalation notification
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.MONITORING_ALERT_ESCALATE,
                content={
                    'pipeline_id': context.pipeline_id,
                    'alert': alert,
                    'escalation_level': alert.get('severity', 'medium')
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name
                )
            )
        )

    async def _resolve_alert(self, context: MonitoringContext, alert: Dict[str, Any]) -> None:
        """
        Resolve a previously detected alert

        Args:
            context (MonitoringContext): Current monitoring context
            alert (Dict[str, Any]): Alert details
        """
        # Resolve alert in context
        context.resolve_alert(alert.get('alert_id'), {'status': 'resolved'})

    async def _handle_metrics_update(self, message: ProcessingMessage) -> None:
        """
        Handle metrics update from monitoring components

        Args:
            message (ProcessingMessage): Message containing metrics update
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_contexts.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for metrics update in pipeline {pipeline_id}")
                return

            # Extract metrics and additional details
            metrics = message.content.get('metrics', {})

            # Update context metrics
            context.update_metrics(metrics)

            # Perform metrics analysis
            analysis_results = await self._analyze_metrics(context, metrics)

            # Publish metrics update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_METRICS_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'metrics': metrics,
                        'analysis': analysis_results,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

            # Check for any threshold violations
            await self._check_metric_thresholds(context, metrics)

        except Exception as e:
            logger.error(f"Metrics update handling failed: {str(e)}")
            await self._handle_error(message, f"Metrics update error: {str(e)}")

    async def _analyze_metrics(self, context: MonitoringContext, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform basic analysis on incoming metrics

        Args:
            context (MonitoringContext): Current monitoring context
            metrics (Dict[str, Any]): Incoming metrics

        Returns:
            Dict[str, Any]: Metrics analysis results
        """
        analysis_results = {}

        # Basic statistical analysis
        for metric_name, metric_value in metrics.items():
            if isinstance(metric_value, (int, float)):
                analysis_results[f'{metric_name}_trend'] = (
                    'increasing' if metric_value > context.metrics.get(metric_name, 0) else 'decreasing'
                )

        return analysis_results

    async def _check_metric_thresholds(self, context: MonitoringContext, metrics: Dict[str, Any]) -> None:
        """
        Check metrics against predefined thresholds

        Args:
            context (MonitoringContext): Current monitoring context
            metrics (Dict[str, Any]): Incoming metrics
        """
        # Predefined thresholds (can be made configurable)
        thresholds = {
            'cpu_usage': {'warning': 80, 'critical': 95},
            'memory_usage': {'warning': 85, 'critical': 95},
            'disk_space': {'warning': 80, 'critical': 90}
        }

        for metric_name, threshold_config in thresholds.items():
            if metric_name in metrics:
                value = metrics[metric_name]
                if value >= threshold_config['critical']:
                    await self.message_broker.publish(
                        ProcessingMessage(
                            message_type=MessageType.MONITORING_ALERT_GENERATE,
                            content={
                                'pipeline_id': context.pipeline_id,
                                'metric': metric_name,
                                'value': value,
                                'severity': 'critical'
                            }
                        )
                    )
                elif value >= threshold_config['warning']:
                    await self.message_broker.publish(
                        ProcessingMessage(
                            message_type=MessageType.MONITORING_ALERT_GENERATE,
                            content={
                                'pipeline_id': context.pipeline_id,
                                'metric': metric_name,
                                'value': value,
                                'severity': 'warning'
                            }
                        )
                    )

    async def _handle_service_start(self, message: ProcessingMessage) -> None:
        """Handle monitoring service start request from manager"""
        try:
            pipeline_id = message.content['pipeline_id']
            config = message.content.get('config', {})

            # Create service context
            context = MonitoringContext(
                pipeline_id=pipeline_id,
                correlation_id=message.metadata.correlation_id,
                monitor_state=MonitoringState.INITIALIZING,
                metric_types=config.get('metric_types', []),
                collectors_enabled=config.get('collectors', []),
                collection_interval=config.get('interval', 60)
            )

            self.active_contexts[pipeline_id] = context

            # Forward to handler to start collection
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_COLLECT_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to handle service start: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_metrics_collected(self, message: ProcessingMessage) -> None:
        """Handle collected metrics from handler"""
        try:
            pipeline_id = message.content['pipeline_id']
            metrics = message.content.get('metrics', {})
            context = self.active_contexts.get(pipeline_id)

            if not context:
                return

            # Process metrics
            context.update_metrics(metrics)

            # Forward processed metrics to manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_SERVICE_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'metrics': metrics,
                        'status': 'metrics_collected'
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to handle metrics collection: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_alert_detected(self, message: ProcessingMessage) -> None:
        """Handle alerts detected by handler"""
        try:
            pipeline_id = message.content['pipeline_id']
            alert = message.content['alert']
            context = self.active_contexts.get(pipeline_id)

            if not context:
                return

            # Process alert
            context.add_alert(alert)

            # Forward alert to manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_SERVICE_ALERT,
                    content={
                        'pipeline_id': pipeline_id,
                        'alert': alert
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to handle alert: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_health_update(self, message: ProcessingMessage) -> None:
        """Handle health status updates from handler"""
        try:
            pipeline_id = message.content['pipeline_id']
            health_status = message.content['health_status']
            context = self.active_contexts.get(pipeline_id)

            if not context:
                return

            # Update health status
            context.update_health_check(health_status)

            # Forward status to manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_SERVICE_HEALTH,
                    content={
                        'pipeline_id': pipeline_id,
                        'health_status': health_status
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to handle health update: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_handler_error(self, message: ProcessingMessage) -> None:
        """Handle errors reported by handler"""
        try:
            pipeline_id = message.content['pipeline_id']
            error = message.content['error']
            context = self.active_contexts.get(pipeline_id)

            if not context:
                return

            # Forward error to manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_SERVICE_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup context
            await self._cleanup_context(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle handler error: {str(e)}")

    async def _handle_service_stop(self, message: ProcessingMessage) -> None:
        """Handle service stop request"""
        try:
            pipeline_id = message.content['pipeline_id']
            context = self.active_contexts.get(pipeline_id)

            if context:
                # Notify handler to stop collection
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.MONITORING_COLLECT_STOP,
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

                # Cleanup
                await self._cleanup_context(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle service stop: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_error(self, message: ProcessingMessage, error: str) -> None:
        """Handle service-level errors"""
        pipeline_id = message.content.get('pipeline_id')
        if not pipeline_id:
            return

        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_SERVICE_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup context
            await self._cleanup_context(pipeline_id)

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    async def _cleanup_context(self, pipeline_id: str) -> None:
        """Cleanup service context"""
        if pipeline_id in self.active_contexts:
            del self.active_contexts[pipeline_id]

    async def cleanup(self) -> None:
        """Cleanup service resources"""
        try:
            # Stop all active monitoring
            for pipeline_id in list(self.active_contexts.keys()):
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.MONITORING_COLLECT_STOP,
                        content={
                            'pipeline_id': pipeline_id,
                            'reason': 'Service cleanup'
                        },
                        metadata=MessageMetadata(
                            source_component=self.module_identifier.component_name,
                            target_component="monitoring_handler"
                        ),
                        source_identifier=self.module_identifier
                    )
                )
                await self._cleanup_context(pipeline_id)

        except Exception as e:
            logger.error(f"Service cleanup failed: {str(e)}")
            raise