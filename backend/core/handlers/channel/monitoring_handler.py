import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    MonitoringContext,
    MonitoringState,
    ComponentType,
    ModuleIdentifier
)
from .base.base_handler import BaseChannelHandler

logger = logging.getLogger(__name__)


class MonitoringHandler(BaseChannelHandler):
    """
    Handler for monitoring operations.
    Routes messages between service and processor layers.
    """

    def __init__(self, message_broker: MessageBroker):
        self.module_identifier = ModuleIdentifier(
            component_name="monitoring_handler",
            component_type=ComponentType.MONITORING_HANDLER,
            department="monitoring",
            role="handler"
        )

        super().__init__(
            message_broker=message_broker,
            module_identifier=self.module_identifier
        )

        # Track active monitoring contexts
        self.active_contexts: Dict[str, MonitoringContext] = {}

    def _setup_message_handlers(self) -> None:
        """Setup message routing handlers"""
        handlers = {
            # From Service Layer
            MessageType.MONITORING_COLLECT_START: self._route_collection_start,
            MessageType.MONITORING_COLLECT_STOP: self._route_collection_stop,
            MessageType.MONITORING_CONFIG_UPDATE: self._route_config_update,

            # From Processor Layer
            MessageType.MONITORING_METRICS_COLLECTED: self._route_metrics_collected,
            MessageType.MONITORING_ALERT_DETECTED: self._route_alert_detected,
            MessageType.MONITORING_HEALTH_STATUS: self._route_health_status,
            MessageType.MONITORING_PROCESSOR_ERROR: self._route_processor_error
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                f"monitoring.{message_type.value}",
                handler
            )

    async def _route_collection_start(self, message: ProcessingMessage) -> None:
        """Route collection start request to processor"""
        try:
            pipeline_id = message.content['pipeline_id']
            config = message.content.get('config', {})

            # Create context
            context = MonitoringContext(
                pipeline_id=pipeline_id,
                correlation_id=message.metadata.correlation_id,
                monitor_state=MonitoringState.INITIALIZING,
                metric_types=config.get('metric_types', []),
                collectors_enabled=config.get('collectors', [])
            )

            self.active_contexts[pipeline_id] = context

            # Forward to processor
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESSOR_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_processor"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to route collection start: {str(e)}")
            await self._handle_error(message, str(e))

    async def _route_metrics_collected(self, message: ProcessingMessage) -> None:
        """Route collected metrics from processor to service"""
        try:
            pipeline_id = message.content['pipeline_id']
            metrics = message.content.get('metrics', {})
            context = self.active_contexts.get(pipeline_id)

            if not context:
                return

            # Forward to service
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_METRICS_COLLECTED,
                    content={
                        'pipeline_id': pipeline_id,
                        'metrics': metrics
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to route metrics: {str(e)}")
            await self._handle_error(message, str(e))

    async def _route_alert_detected(self, message: ProcessingMessage) -> None:
        """Route detected alerts from processor to service"""
        try:
            pipeline_id = message.content['pipeline_id']
            alert = message.content['alert']
            context = self.active_contexts.get(pipeline_id)

            if not context:
                return

            # Forward to service
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_DETECTED,
                    content={
                        'pipeline_id': pipeline_id,
                        'alert': alert
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to route alert: {str(e)}")
            await self._handle_error(message, str(e))

    async def _route_health_status(self, message: ProcessingMessage) -> None:
        """Route health status from processor to service"""
        try:
            pipeline_id = message.content['pipeline_id']
            health_status = message.content['health_status']
            context = self.active_contexts.get(pipeline_id)

            if not context:
                return

            # Forward to service
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_HEALTH_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'health_status': health_status
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to route health status: {str(e)}")
            await self._handle_error(message, str(e))

    async def _route_collection_stop(self, message: ProcessingMessage) -> None:
        """Route collection stop request to processor"""
        try:
            pipeline_id = message.content['pipeline_id']
            context = self.active_contexts.get(pipeline_id)

            if not context:
                return

            # Forward to processor
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESSOR_STOP,
                    content={
                        'pipeline_id': pipeline_id
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_processor"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup context
            await self._cleanup_context(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to route collection stop: {str(e)}")
            await self._handle_error(message, str(e))

    async def _route_processor_error(self, message: ProcessingMessage) -> None:
        """Route processor errors to service"""
        try:
            pipeline_id = message.content['pipeline_id']
            error = message.content['error']
            context = self.active_contexts.get(pipeline_id)

            if not context:
                return

            # Forward to service
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_HANDLER_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup context
            await self._cleanup_context(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to route processor error: {str(e)}")

    async def _handle_error(self, message: ProcessingMessage, error: str) -> None:
        """Handle handler-level errors"""
        pipeline_id = message.content.get('pipeline_id')
        if not pipeline_id:
            return

        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_HANDLER_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup context
            await self._cleanup_context(pipeline_id)

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    async def _cleanup_context(self, pipeline_id: str) -> None:
        """Cleanup handler context"""
        if pipeline_id in self.active_contexts:
            del self.active_contexts[pipeline_id]

    async def cleanup(self) -> None:
        """Cleanup handler resources"""
        try:
            # Stop all active monitoring
            for pipeline_id in list(self.active_contexts.keys()):
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.MONITORING_PROCESSOR_STOP,
                        content={
                            'pipeline_id': pipeline_id,
                            'reason': 'Handler cleanup'
                        },
                        metadata=MessageMetadata(
                            source_component=self.module_identifier.component_name,
                            target_component="monitoring_processor"
                        ),
                        source_identifier=self.module_identifier
                    )
                )
                await self._cleanup_context(pipeline_id)

        except Exception as e:
            logger.error(f"Handler cleanup failed: {str(e)}")
            raise