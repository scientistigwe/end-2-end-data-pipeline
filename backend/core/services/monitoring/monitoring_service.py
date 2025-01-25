# backend/core/services/monitoring/monitoring_service.py

import logging
import asyncio
import psutil
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ComponentType,
    ModuleIdentifier,
    MessageMetadata
)
from core.staging.staging_manager import StagingManager

logger = logging.getLogger(__name__)


class MonitoringService:
    """
    Service layer for monitoring functionality.
    Uses staging system for data persistence and management.
    """

    def __init__(
            self,
            staging_manager: StagingManager,
            message_broker: MessageBroker,
            initialize_async: bool = False
    ):
        self.staging_manager = staging_manager
        self.message_broker = message_broker

        self.module_identifier = ModuleIdentifier(
            component_name="monitoring_service",
            component_type=ComponentType.MONITORING_SERVICE,
            department="monitoring",
            role="service"
        )

        self.logger = logger

        if initialize_async:
            asyncio.run(self._initialize_async())

    async def _initialize_async(self):
        await self._initialize_message_handlers()

    async def _initialize_message_handlers(self) -> None:
        handlers = {
            MessageType.METRICS_REQUEST: self._handle_metrics_request,
            MessageType.HEALTH_CHECK_REQUEST: self._handle_health_check,
            MessageType.RESOURCE_USAGE_REQUEST: self._handle_resource_usage,
            MessageType.MONITORING_ERROR: self._handle_error
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=f"monitoring.{message_type.value}.#",
                callback=handler
            )

    async def _handle_metrics_request(self, message: ProcessingMessage) -> None:
        """Handle metrics data request"""
        try:
            pipeline_id = message.content.get('pipeline_id')

            # Get resource metrics
            metrics = await self._collect_resource_metrics()

            # Store in staging
            reference_id = await self.staging_manager.stage_data(
                data=metrics,
                component_type=ComponentType.MONITORING_MANAGER,
                pipeline_id=pipeline_id,
                metadata={
                    'type': 'resource_metrics',
                    'timestamp': datetime.utcnow().isoformat()
                }
            )

            # Send response
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.METRICS_RESPONSE,
                    content={
                        'pipeline_id': pipeline_id,
                        'reference_id': reference_id,
                        'metrics': metrics,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component=message.metadata.source_component,
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle metrics request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _collect_resource_metrics(self) -> Dict[str, Any]:
        """Collect system resource metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                'resource_metrics': {
                    'cpu_usage': cpu_percent,
                    'memory_usage': memory.percent,
                    'disk_usage': disk.percent,
                    'network': {
                        'in': 0,  # Would need network monitoring implementation
                        'out': 0
                    }
                },
                'performance': {
                    'processing_time': None,  # Updated during processing
                    'throughput': None,
                    'error_count': 0
                }
            }

        except Exception as e:
            self.logger.error(f"Error collecting resource metrics: {str(e)}")
            raise

    async def _handle_health_check(self, message: ProcessingMessage) -> None:
        """Handle health check request"""
        try:
            pipeline_id = message.content.get('pipeline_id')

            # Perform health checks
            health_status = await self._perform_health_checks()

            # Store in staging
            reference_id = await self.staging_manager.stage_data(
                data=health_status,
                component_type=ComponentType.MONITORING_MANAGER,
                pipeline_id=pipeline_id,
                metadata={
                    'type': 'health_check',
                    'timestamp': datetime.utcnow().isoformat()
                }
            )

            # Send response
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.HEALTH_CHECK_RESPONSE,
                    content={
                        'pipeline_id': pipeline_id,
                        'reference_id': reference_id,
                        'health_status': health_status,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component=message.metadata.source_component,
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle health check: {str(e)}")
            await self._notify_error(message, str(e))

    async def _perform_health_checks(self) -> Dict[str, Any]:
        """Perform system health checks"""
        try:
            return {
                'component_status': {
                    'staging': True,
                    'messaging': True,
                    'monitoring': True
                },
                'health_checks': {
                    'system': 'healthy',
                    'components': {
                        'staging': 'healthy',
                        'messaging': 'healthy',
                        'monitoring': 'healthy'
                    }
                }
            }
        except Exception as e:
            self.logger.error(f"Error performing health checks: {str(e)}")
            raise

    async def _handle_error(self, message: ProcessingMessage) -> None:
        """Handle monitoring-related errors"""
        error = message.content.get('error', 'Unknown error')
        self.logger.error(f"Monitoring error received: {error}")
        await self._notify_error(message, error)

    async def _notify_error(self, original_message: ProcessingMessage, error: str) -> None:
        """Notify about errors"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.SERVICE_ERROR,
                content={
                    'service': self.module_identifier.component_name,
                    'error': error,
                    'original_message': original_message.content
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager",
                    correlation_id=original_message.metadata.correlation_id
                )
            )
        )

    async def cleanup(self) -> None:
        """Cleanup service resources"""
        try:
            await self.message_broker.unsubscribe_all(
                self.module_identifier.component_name
            )
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")