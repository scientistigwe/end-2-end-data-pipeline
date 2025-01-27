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

    def _setup_message_handlers(self) -> None:
        """Setup handlers for service-level messages"""
        handlers = {
            # From Manager
            MessageType.MONITORING_SERVICE_START: self._handle_service_start,
            MessageType.MONITORING_SERVICE_STOP: self._handle_service_stop,
            MessageType.MONITORING_CONFIG_UPDATE: self._handle_config_update,

            # From Handler
            MessageType.MONITORING_METRICS_COLLECTED: self._handle_metrics_collected,
            MessageType.MONITORING_ALERT_DETECTED: self._handle_alert_detected,
            MessageType.MONITORING_HEALTH_UPDATE: self._handle_health_update,
            MessageType.MONITORING_HANDLER_ERROR: self._handle_handler_error
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                f"monitoring.{message_type.value}",
                handler
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