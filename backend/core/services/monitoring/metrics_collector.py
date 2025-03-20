import asyncio
import psutil
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from ..base.base_service import BaseService
from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    MonitoringMetrics,
    MetricType,
    MonitoringContext,
    MetricsAggregate
)

logger = logging.getLogger(__name__)

class MetricsCollector(BaseService):
    """
    Service for collecting real-time system metrics.
    Handles various types of metrics collection and aggregation.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker)
        
        # Service identifier
        self.module_identifier = ModuleIdentifier(
            component_name="metrics_collector",
            component_type=ComponentType.MONITORING_SERVICE,
            department="monitoring",
            role="collector"
        )

        # Collection configuration
        self.collection_interval = 60  # seconds
        self.active_collections: Dict[str, asyncio.Task] = {}
        self.metric_buffers: Dict[str, List[Dict[str, Any]]] = {}
        self.buffer_size = 1000

        # Setup message handlers
        self._setup_message_handlers()

    async def _setup_message_handlers(self) -> None:
        """Setup handlers for collector-level messages"""
        handlers = {
            MessageType.MONITORING_METRICS_COLLECT: self._handle_collection_request,
            MessageType.MONITORING_CONFIG_UPDATE: self._handle_config_update,
            MessageType.MONITORING_PROCESS_COMPLETE: self._handle_collection_stop
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_collection_request(self, message: ProcessingMessage) -> None:
        """Handle request to start metrics collection"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            if not pipeline_id:
                raise ValueError("Pipeline ID is required")

            # Extract collection configuration
            config = message.content.get('config', {})
            metric_types = config.get('metric_types', [])
            interval = config.get('collection_interval', self.collection_interval)

            # Create collection context
            context = MonitoringContext(
                pipeline_id=pipeline_id,
                metric_types=metric_types,
                collection_interval=interval
            )

            # Start collection task if not already running
            if pipeline_id not in self.active_collections:
                collection_task = asyncio.create_task(
                    self._collect_metrics(context)
                )
                self.active_collections[pipeline_id] = collection_task

            # Publish collection start notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_METRICS_COLLECT,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'started',
                        'config': config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to start metrics collection: {str(e)}")
            await self._handle_error(message, str(e))

    async def _collect_metrics(self, context: MonitoringContext) -> None:
        """Collect metrics based on configuration"""
        try:
            while True:
                metrics = await self._gather_metrics(context)
                
                # Buffer metrics
                if context.pipeline_id not in self.metric_buffers:
                    self.metric_buffers[context.pipeline_id] = []
                
                self.metric_buffers[context.pipeline_id].append(metrics)

                # Publish metrics if buffer is full
                if len(self.metric_buffers[context.pipeline_id]) >= self.buffer_size:
                    await self._publish_buffered_metrics(context)

                # Wait for next collection interval
                await asyncio.sleep(context.collection_interval)

        except asyncio.CancelledError:
            logger.info(f"Metrics collection cancelled for pipeline {context.pipeline_id}")
        except Exception as e:
            logger.error(f"Error in metrics collection: {str(e)}")
            await self._handle_error(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESS_FAILED,
                    content={'pipeline_id': context.pipeline_id}
                ),
                str(e)
            )

    async def _gather_metrics(self, context: MonitoringContext) -> Dict[str, Any]:
        """Gather system metrics based on configuration"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'pipeline_id': context.pipeline_id,
            'metrics': {}
        }

        # System metrics
        if MetricType.SYSTEM in context.metric_types:
            metrics['metrics']['system'] = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_io': {
                    'bytes_sent': psutil.net_io_counters().bytes_sent,
                    'bytes_recv': psutil.net_io_counters().bytes_recv
                }
            }

        # Performance metrics
        if MetricType.PERFORMANCE in context.metric_types:
            metrics['metrics']['performance'] = {
                'cpu_times': psutil.cpu_times()._asdict(),
                'memory_stats': psutil.virtual_memory()._asdict(),
                'disk_io': psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {}
            }

        # Resource metrics
        if MetricType.RESOURCE in context.metric_types:
            metrics['metrics']['resource'] = {
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'disk_total': psutil.disk_usage('/').total,
                'process_count': len(psutil.pids())
            }

        return metrics

    async def _publish_buffered_metrics(self, context: MonitoringContext) -> None:
        """Publish buffered metrics"""
        try:
            metrics = self.metric_buffers[context.pipeline_id]
            
            # Aggregate metrics
            aggregated = self._aggregate_metrics(metrics)
            
            # Create metrics aggregate
            metrics_aggregate = MetricsAggregate(
                metric_id=str(uuid.uuid4()),
                metric_type=MetricType.SYSTEM,  # Default type, can be enhanced
                value=aggregated['system']['cpu_percent'],  # Example value
                timestamp=datetime.now(),
                source=self.module_identifier.component_name,
                aggregation_type='average',
                dimensions={'pipeline_id': context.pipeline_id},
                metadata={'raw_metrics': metrics}
            )

            # Publish aggregated metrics
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_METRICS_UPDATE,
                    content={
                        'pipeline_id': context.pipeline_id,
                        'metrics': aggregated,
                        'aggregate': metrics_aggregate
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

            # Clear buffer
            self.metric_buffers[context.pipeline_id] = []

        except Exception as e:
            logger.error(f"Failed to publish metrics: {str(e)}")
            await self._handle_error(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESS_FAILED,
                    content={'pipeline_id': context.pipeline_id}
                ),
                str(e)
            )

    def _aggregate_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate collected metrics"""
        aggregated = {
            'system': {},
            'performance': {},
            'resource': {}
        }

        # Calculate averages for numeric metrics
        for metric in metrics:
            for category, values in metric['metrics'].items():
                if category not in aggregated:
                    aggregated[category] = {}
                
                for key, value in values.items():
                    if isinstance(value, (int, float)):
                        if key not in aggregated[category]:
                            aggregated[category][key] = []
                        aggregated[category][key].append(value)
                    else:
                        aggregated[category][key] = value

        # Calculate averages
        for category in aggregated:
            for key in aggregated[category]:
                if isinstance(aggregated[category][key], list):
                    aggregated[category][key] = sum(aggregated[category][key]) / len(aggregated[category][key])

        return aggregated

    async def _handle_config_update(self, message: ProcessingMessage) -> None:
        """Handle configuration updates"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            if not pipeline_id:
                raise ValueError("Pipeline ID is required")

            config = message.content.get('config', {})
            
            # Update collection interval if provided
            if 'collection_interval' in config:
                self.collection_interval = config['collection_interval']

            # Update buffer size if provided
            if 'buffer_size' in config:
                self.buffer_size = config['buffer_size']

            # Publish configuration update acknowledgment
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_CONFIG_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'updated',
                        'config': config
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to update configuration: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_collection_stop(self, message: ProcessingMessage) -> None:
        """Handle request to stop metrics collection"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            if not pipeline_id:
                raise ValueError("Pipeline ID is required")

            # Cancel collection task if running
            if pipeline_id in self.active_collections:
                self.active_collections[pipeline_id].cancel()
                del self.active_collections[pipeline_id]

            # Clear metric buffer
            if pipeline_id in self.metric_buffers:
                del self.metric_buffers[pipeline_id]

            # Publish collection stop notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESS_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'stopped'
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to stop metrics collection: {str(e)}")
            await self._handle_error(message, str(e)) 