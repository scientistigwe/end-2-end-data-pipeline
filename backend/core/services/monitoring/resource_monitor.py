import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import psutil
import numpy as np

from ..base.base_service import BaseService
from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    MonitoringContext,
    MetricType,
    ResourceMetrics,
    ResourceThreshold,
    ResourceAlert
)

logger = logging.getLogger(__name__)

class ResourceMonitor(BaseService):
    """
    Service for monitoring system resources.
    Handles resource usage tracking, threshold monitoring, and alert generation.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker)
        
        # Service identifier
        self.module_identifier = ModuleIdentifier(
            component_name="resource_monitor",
            component_type=ComponentType.MONITORING_SERVICE,
            department="monitoring",
            role="monitor"
        )

        # Resource monitoring configuration
        self.monitoring_interval = 60  # seconds
        self.history_window = timedelta(hours=24)
        self.alert_cooldown = timedelta(minutes=5)
        
        # Resource thresholds
        self.thresholds: Dict[str, Dict[str, float]] = {
            'cpu': {
                'warning': 80.0,  # CPU usage percentage
                'critical': 90.0
            },
            'memory': {
                'warning': 85.0,  # Memory usage percentage
                'critical': 95.0
            },
            'disk': {
                'warning': 85.0,  # Disk usage percentage
                'critical': 95.0
            },
            'network': {
                'warning': 80.0,  # Network bandwidth usage percentage
                'critical': 90.0
            }
        }
        
        # Resource monitoring state
        self.resource_history: Dict[str, List[Dict[str, Any]]] = {}
        self.last_alerts: Dict[str, datetime] = {}
        self.active_monitoring: Dict[str, asyncio.Task] = {}
        
        # Setup message handlers
        self._setup_message_handlers()

    async def _setup_message_handlers(self) -> None:
        """Setup handlers for resource monitoring messages"""
        handlers = {
            MessageType.MONITORING_RESOURCE_START: self._handle_monitoring_start,
            MessageType.MONITORING_RESOURCE_STOP: self._handle_monitoring_stop,
            MessageType.MONITORING_THRESHOLD_UPDATE: self._handle_threshold_update
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_monitoring_start(self, message: ProcessingMessage) -> None:
        """Handle request to start resource monitoring"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            if not pipeline_id:
                raise ValueError("Pipeline ID is required")

            # Start monitoring if not already running
            if pipeline_id not in self.active_monitoring:
                monitoring_task = asyncio.create_task(
                    self._monitor_resources(pipeline_id)
                )
                self.active_monitoring[pipeline_id] = monitoring_task

            # Initialize resource history if needed
            if pipeline_id not in self.resource_history:
                self.resource_history[pipeline_id] = []

            # Publish monitoring start notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_RESOURCE_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'started'
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to start resource monitoring: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_monitoring_stop(self, message: ProcessingMessage) -> None:
        """Handle request to stop resource monitoring"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            if not pipeline_id:
                raise ValueError("Pipeline ID is required")

            # Stop monitoring if running
            if pipeline_id in self.active_monitoring:
                self.active_monitoring[pipeline_id].cancel()
                del self.active_monitoring[pipeline_id]

            # Publish monitoring stop notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_RESOURCE_STOP,
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
            logger.error(f"Failed to stop resource monitoring: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_threshold_update(self, message: ProcessingMessage) -> None:
        """Handle resource threshold updates"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            if not pipeline_id:
                raise ValueError("Pipeline ID is required")

            thresholds = message.content.get('thresholds', {})
            if not thresholds:
                raise ValueError("No thresholds provided")

            # Update thresholds
            for resource, levels in thresholds.items():
                if resource in self.thresholds:
                    self.thresholds[resource].update(levels)

            # Publish threshold update notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_THRESHOLD_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'thresholds': self.thresholds,
                        'status': 'updated'
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to update thresholds: {str(e)}")
            await self._handle_error(message, str(e))

    async def _monitor_resources(self, pipeline_id: str) -> None:
        """Monitor system resources"""
        try:
            while True:
                # Collect resource metrics
                metrics = await self._collect_resource_metrics()
                
                # Store metrics in history
                self.resource_history[pipeline_id].append({
                    'timestamp': datetime.now(),
                    'metrics': metrics
                })

                # Clean up old metrics
                self._cleanup_old_metrics(pipeline_id)

                # Check thresholds and generate alerts
                await self._check_thresholds(pipeline_id, metrics)

                # Wait for next monitoring interval
                await asyncio.sleep(self.monitoring_interval)

        except asyncio.CancelledError:
            logger.info(f"Resource monitoring cancelled for pipeline {pipeline_id}")
        except Exception as e:
            logger.error(f"Error in resource monitoring: {str(e)}")
            await self._handle_error(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESS_FAILED,
                    content={'pipeline_id': pipeline_id}
                ),
                str(e)
            )

    async def _collect_resource_metrics(self) -> Dict[str, Any]:
        """Collect system resource metrics"""
        metrics = {
            'cpu': {
                'percent': psutil.cpu_percent(interval=1),
                'count': psutil.cpu_count(),
                'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
                'times': psutil.cpu_times()._asdict()
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent,
                'used': psutil.virtual_memory().used,
                'free': psutil.virtual_memory().free
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent
            },
            'network': {
                'bytes_sent': psutil.net_io_counters().bytes_sent,
                'bytes_recv': psutil.net_io_counters().bytes_recv,
                'packets_sent': psutil.net_io_counters().packets_sent,
                'packets_recv': psutil.net_io_counters().packets_recv
            }
        }

        return metrics

    def _cleanup_old_metrics(self, pipeline_id: str) -> None:
        """Remove metrics older than the history window"""
        if pipeline_id not in self.resource_history:
            return

        cutoff_time = datetime.now() - self.history_window
        self.resource_history[pipeline_id] = [
            entry for entry in self.resource_history[pipeline_id]
            if entry['timestamp'] > cutoff_time
        ]

    async def _check_thresholds(self, pipeline_id: str, metrics: Dict[str, Any]) -> None:
        """Check resource metrics against thresholds and generate alerts"""
        alerts = []

        # Check CPU usage
        cpu_percent = metrics['cpu']['percent']
        if cpu_percent >= self.thresholds['cpu']['critical']:
            alerts.append(self._create_alert('cpu', 'critical', cpu_percent))
        elif cpu_percent >= self.thresholds['cpu']['warning']:
            alerts.append(self._create_alert('cpu', 'warning', cpu_percent))

        # Check memory usage
        memory_percent = metrics['memory']['percent']
        if memory_percent >= self.thresholds['memory']['critical']:
            alerts.append(self._create_alert('memory', 'critical', memory_percent))
        elif memory_percent >= self.thresholds['memory']['warning']:
            alerts.append(self._create_alert('memory', 'warning', memory_percent))

        # Check disk usage
        disk_percent = metrics['disk']['percent']
        if disk_percent >= self.thresholds['disk']['critical']:
            alerts.append(self._create_alert('disk', 'critical', disk_percent))
        elif disk_percent >= self.thresholds['disk']['warning']:
            alerts.append(self._create_alert('disk', 'warning', disk_percent))

        # Check network usage (if bandwidth monitoring is enabled)
        if 'network' in metrics:
            network_metrics = metrics['network']
            # Calculate network bandwidth usage (example)
            total_bytes = network_metrics['bytes_sent'] + network_metrics['bytes_recv']
            if total_bytes > 0:
                network_percent = (network_metrics['bytes_sent'] / total_bytes) * 100
                if network_percent >= self.thresholds['network']['critical']:
                    alerts.append(self._create_alert('network', 'critical', network_percent))
                elif network_percent >= self.thresholds['network']['warning']:
                    alerts.append(self._create_alert('network', 'warning', network_percent))

        # Publish alerts if any
        if alerts:
            await self._publish_alerts(pipeline_id, alerts)

    def _create_alert(self, resource: str, level: str, value: float) -> ResourceAlert:
        """Create a resource alert"""
        return ResourceAlert(
            resource=resource,
            level=level,
            value=value,
            threshold=self.thresholds[resource][level],
            timestamp=datetime.now()
        )

    async def _publish_alerts(self, pipeline_id: str, alerts: List[ResourceAlert]) -> None:
        """Publish resource alerts"""
        try:
            current_time = datetime.now()
            
            # Check alert cooldown
            for alert in alerts:
                alert_key = f"{pipeline_id}_{alert.resource}_{alert.level}"
                if alert_key in self.last_alerts:
                    if current_time - self.last_alerts[alert_key] < self.alert_cooldown:
                        continue
                
                # Publish alert
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.MONITORING_RESOURCE_ALERT,
                        content={
                            'pipeline_id': pipeline_id,
                            'alert': alert
                        },
                        metadata=MessageMetadata(
                            correlation_id=str(uuid.uuid4()),
                            source_component=self.module_identifier.component_name
                        )
                    )
                )
                
                # Update last alert time
                self.last_alerts[alert_key] = current_time

        except Exception as e:
            logger.error(f"Failed to publish resource alerts: {str(e)}")
            await self._handle_error(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESS_FAILED,
                    content={'pipeline_id': pipeline_id}
                ),
                str(e)
            ) 