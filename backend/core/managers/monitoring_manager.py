import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import psutil
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    MessageMetadata,
    MonitoringContext,
    MonitoringState,
    ManagerState,
    MonitoringMetrics
)
from .base.base_manager import BaseManager

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of metrics that can be monitored"""
    SYSTEM = "system"
    PROCESS = "process"
    PERFORMANCE = "performance"
    RESOURCE = "resource"
    CUSTOM = "custom"

@dataclass
class MetricThreshold:
    """Threshold configuration for metrics"""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    comparison: str  # 'gt' (greater than) or 'lt' (less than)
    window_size: int  # Number of samples to consider
    cooldown_period: int  # Seconds to wait before alerting again

class MonitoringManager(BaseManager):
    """
    Monitoring Manager: Coordinates system monitoring and metrics collection.
    Manages metric collection, threshold monitoring, and alert generation.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            component_name: str = "monitoring_manager",
            domain_type: str = "monitoring"
    ):
        super().__init__(
            message_broker=message_broker,
            component_name=component_name,
            domain_type=domain_type
        )

        # Active monitoring contexts
        self.active_contexts: Dict[str, MonitoringContext] = {}
        self.metric_history: Dict[str, List[Dict[str, Any]]] = {}
        self.alert_history: Dict[str, List[Dict[str, Any]]] = {}
        self.last_alert_time: Dict[str, datetime] = {}

        # Configuration
        self.monitoring_config = {
            "max_retries": 3,
            "timeout_seconds": 300,
            "batch_size": 1000,
            "max_concurrent_monitoring": 5,
            "metric_collection": {
                "interval": 60,  # seconds
                "history_size": 1000,
                "aggregation_window": 300  # seconds
            },
            "alerting": {
                "cooldown_period": 300,  # seconds
                "max_alerts_per_hour": 10,
                "alert_channels": ["log", "message_broker"]
            },
            "thresholds": {
                "cpu_percent": MetricThreshold(
                    metric_name="cpu_percent",
                    warning_threshold=80.0,
                    critical_threshold=90.0,
                    comparison="gt",
                    window_size=5,
                    cooldown_period=300
                ),
                "memory_percent": MetricThreshold(
                    metric_name="memory_percent",
                    warning_threshold=80.0,
                    critical_threshold=90.0,
                    comparison="gt",
                    window_size=5,
                    cooldown_period=300
                ),
                "disk_usage": MetricThreshold(
                    metric_name="disk_usage",
                    warning_threshold=80.0,
                    critical_threshold=90.0,
                    comparison="gt",
                    window_size=5,
                    cooldown_period=300
                )
            }
        }

        # Initialize state
        self.state = ManagerState.INITIALIZING

    async def _setup_domain_handlers(self) -> None:
        """Setup monitoring-specific message handlers"""
        handlers = {
            # Core Flow
            MessageType.MONITORING_START_REQUEST: self._handle_start_request,
            MessageType.MONITORING_START: self._handle_start,
            MessageType.MONITORING_PROGRESS: self._handle_progress,
            MessageType.MONITORING_COMPLETE: self._handle_complete,
            MessageType.MONITORING_FAILED: self._handle_failed,

            # Metric Collection
            MessageType.MONITORING_METRIC_COLLECT: self._handle_metric_collect,
            MessageType.MONITORING_METRIC_UPDATE: self._handle_metric_update,
            MessageType.MONITORING_METRIC_ALERT: self._handle_metric_alert,

            # Threshold Management
            MessageType.MONITORING_THRESHOLD_UPDATE: self._handle_threshold_update,
            MessageType.MONITORING_THRESHOLD_VIOLATION: self._handle_threshold_violation,

            # Alert Management
            MessageType.MONITORING_ALERT_CREATE: self._handle_alert_create,
            MessageType.MONITORING_ALERT_RESOLVE: self._handle_alert_resolve,
            MessageType.MONITORING_ALERT_ACKNOWLEDGE: self._handle_alert_acknowledge,

            # Resource Management
            MessageType.MONITORING_RESOURCE_REQUEST: self._handle_resource_request,
            MessageType.MONITORING_RESOURCE_RELEASE: self._handle_resource_release,

            # System Operations
            MessageType.MONITORING_HEALTH_CHECK: self._handle_health_check,
            MessageType.MONITORING_CONFIG_UPDATE: self._handle_config_update
        }

        for message_type, handler in handlers.items():
            await self.register_message_handler(message_type, handler)

    def _start_background_tasks(self) -> None:
        """Start background monitoring tasks"""
        asyncio.create_task(self._monitor_system_metrics())
        asyncio.create_task(self._check_thresholds())
        asyncio.create_task(self._cleanup_old_metrics())

    async def _monitor_system_metrics(self) -> None:
        """Monitor system metrics continuously"""
        while self.state == ManagerState.ACTIVE:
            try:
                metrics = await self._collect_system_metrics()
                await self._process_metrics(metrics)
                await asyncio.sleep(self.monitoring_config["metric_collection"]["interval"])
            except Exception as e:
                logger.error(f"System metric monitoring failed: {str(e)}")
                await asyncio.sleep(60)

    async def _collect_system_metrics(self) -> Dict[str, float]:
        """Collect system metrics"""
        try:
            metrics = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "network_io": {
                    "bytes_sent": psutil.net_io_counters().bytes_sent,
                    "bytes_recv": psutil.net_io_counters().bytes_recv
                },
                "process_count": len(psutil.pids()),
                "thread_count": sum(p.num_threads() for p in psutil.process_iter(['num_threads'])),
                "timestamp": datetime.now().isoformat()
            }
            return metrics
        except Exception as e:
            logger.error(f"System metric collection failed: {str(e)}")
            return {}

    async def _process_metrics(self, metrics: Dict[str, Any]) -> None:
        """Process collected metrics"""
        try:
            # Store metrics in history
            for metric_name, value in metrics.items():
                if metric_name not in self.metric_history:
                    self.metric_history[metric_name] = []
                
                self.metric_history[metric_name].append({
                    "value": value,
                    "timestamp": datetime.now().isoformat()
                })

                # Trim history if needed
                if len(self.metric_history[metric_name]) > self.monitoring_config["metric_collection"]["history_size"]:
                    self.metric_history[metric_name] = self.metric_history[metric_name][-self.monitoring_config["metric_collection"]["history_size"]:]

            # Check thresholds
            await self._check_thresholds()

            # Publish metric update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_METRIC_UPDATE,
                    content={
                        "metrics": metrics,
                        "timestamp": datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="monitoring_service"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Metric processing failed: {str(e)}")

    async def _check_thresholds(self) -> None:
        """Check metric thresholds"""
        try:
            for metric_name, threshold in self.monitoring_config["thresholds"].items():
                if metric_name in self.metric_history:
                    recent_values = [m["value"] for m in self.metric_history[metric_name][-threshold.window_size:]]
                    if len(recent_values) >= threshold.window_size:
                        avg_value = sum(recent_values) / len(recent_values)
                        await self._evaluate_threshold(metric_name, avg_value, threshold)

        except Exception as e:
            logger.error(f"Threshold checking failed: {str(e)}")

    async def _evaluate_threshold(self, metric_name: str, value: float, threshold: MetricThreshold) -> None:
        """Evaluate metric against threshold"""
        try:
            current_time = datetime.now()
            last_alert = self.last_alert_time.get(metric_name)
            
            if last_alert and (current_time - last_alert).total_seconds() < threshold.cooldown_period:
                return

            is_violation = False
            severity = None

            if threshold.comparison == "gt":
                if value >= threshold.critical_threshold:
                    is_violation = True
                    severity = "critical"
                elif value >= threshold.warning_threshold:
                    is_violation = True
                    severity = "warning"
            else:  # lt
                if value <= threshold.critical_threshold:
                    is_violation = True
                    severity = "critical"
                elif value <= threshold.warning_threshold:
                    is_violation = True
                    severity = "warning"

            if is_violation:
                await self._handle_threshold_violation(metric_name, value, threshold, severity)
                self.last_alert_time[metric_name] = current_time

        except Exception as e:
            logger.error(f"Threshold evaluation failed: {str(e)}")

    async def _handle_threshold_violation(self, metric_name: str, value: float, threshold: MetricThreshold, severity: str) -> None:
        """Handle threshold violation"""
        try:
            alert_id = str(uuid.uuid4())
            alert = {
                "alert_id": alert_id,
                "metric_name": metric_name,
                "value": value,
                "threshold": threshold.__dict__,
                "severity": severity,
                "timestamp": datetime.now().isoformat(),
                "status": "active"
            }

            # Store alert
            if metric_name not in self.alert_history:
                self.alert_history[metric_name] = []
            self.alert_history[metric_name].append(alert)

            # Publish alert
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_CREATE,
                    content=alert,
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="alert_service"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Threshold violation handling failed: {str(e)}")

    async def _cleanup_old_metrics(self) -> None:
        """Clean up old metrics"""
        while self.state == ManagerState.ACTIVE:
            try:
                current_time = datetime.now()
                cutoff_time = current_time - timedelta(hours=24)  # Keep last 24 hours

                for metric_name in self.metric_history:
                    self.metric_history[metric_name] = [
                        m for m in self.metric_history[metric_name]
                        if datetime.fromisoformat(m["timestamp"]) > cutoff_time
                    ]

                await asyncio.sleep(3600)  # Run every hour

            except Exception as e:
                logger.error(f"Metric cleanup failed: {str(e)}")
                await asyncio.sleep(300)

    async def _handle_start_request(self, message: ProcessingMessage) -> None:
        """Handle monitoring start request"""
        try:
            monitoring_id = message.content.get('monitoring_id')
            config = message.content.get('config', {})

            # Validate configuration
            if not self._validate_monitoring_config(config):
                raise ValueError("Invalid monitoring configuration")

            # Create monitoring context
            context = MonitoringContext(
                monitoring_id=monitoring_id,
                correlation_id=str(uuid.uuid4()),
                state=MonitoringState.INITIALIZING,
                config=config,
                metrics=MonitoringMetrics()
            )

            self.active_contexts[monitoring_id] = context

            # Start monitoring
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_START,
                    content={
                        'monitoring_id': monitoring_id,
                        'config': config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="monitoring_service"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Start request failed: {str(e)}")
            await self._handle_error(message.content.get('monitoring_id'), str(e))

    def _validate_monitoring_config(self, config: Dict[str, Any]) -> bool:
        """Validate monitoring configuration"""
        try:
            required_fields = ['metrics', 'thresholds', 'alerting']
            if not all(field in config for field in required_fields):
                return False

            # Validate metrics
            if not isinstance(config['metrics'], list):
                return False

            # Validate thresholds
            if not isinstance(config['thresholds'], dict):
                return False

            # Validate alerting
            if not isinstance(config['alerting'], dict):
                return False

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False

    async def _handle_start(self, message: ProcessingMessage) -> None:
        """Handle monitoring start"""
        monitoring_id = message.content.get('monitoring_id')
        context = self.active_contexts.get(monitoring_id)

        if not context:
            return

        try:
            context.state = MonitoringState.ACTIVE
            context.updated_at = datetime.now()

            # Initialize metric collection
            await self._initialize_metric_collection(monitoring_id)

        except Exception as e:
            logger.error(f"Monitoring start failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _initialize_metric_collection(self, monitoring_id: str) -> None:
        """Initialize metric collection"""
        try:
            context = self.active_contexts.get(monitoring_id)
            if not context:
                return

            # Start metric collection tasks
            for metric in context.config['metrics']:
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.MONITORING_METRIC_COLLECT,
                        content={
                            'monitoring_id': monitoring_id,
                            'metric': metric
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component="monitoring_service"
                        )
                    )
                )

        except Exception as e:
            logger.error(f"Metric collection initialization failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _handle_progress(self, message: ProcessingMessage) -> None:
        """Handle monitoring progress updates"""
        monitoring_id = message.content.get('monitoring_id')
        progress = message.content.get('progress', 0)
        context = self.active_contexts.get(monitoring_id)

        if not context:
            return

        try:
            context.progress = progress
            context.updated_at = datetime.now()

        except Exception as e:
            logger.error(f"Progress update failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _handle_complete(self, message: ProcessingMessage) -> None:
        """Handle monitoring completion"""
        monitoring_id = message.content.get('monitoring_id')
        results = message.content.get('results', {})
        context = self.active_contexts.get(monitoring_id)

        if not context:
            return

        try:
            context.state = MonitoringState.COMPLETED
            context.completed_at = datetime.now()
            context.results = results

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_COMPLETE,
                    content={
                        'monitoring_id': monitoring_id,
                        'results': results
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="monitoring_service"
                    )
                )
            )

            await self._cleanup_monitoring(monitoring_id)

        except Exception as e:
            logger.error(f"Completion failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _handle_failed(self, message: ProcessingMessage) -> None:
        """Handle monitoring failure"""
        monitoring_id = message.content.get('monitoring_id')
        error = message.content.get('error', 'Unknown error')
        await self._handle_error(monitoring_id, error)

    async def _handle_metric_collect(self, message: ProcessingMessage) -> None:
        """Handle metric collection request"""
        monitoring_id = message.content.get('monitoring_id')
        metric = message.content.get('metric')
        context = self.active_contexts.get(monitoring_id)

        if not context:
            return

        try:
            # Collect metric value
            value = await self._collect_metric(metric)
            
            # Update context
            context.metrics.__dict__[metric] = value
            context.updated_at = datetime.now()

            # Publish metric update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_METRIC_UPDATE,
                    content={
                        'monitoring_id': monitoring_id,
                        'metric': metric,
                        'value': value
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="monitoring_service"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Metric collection failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _collect_metric(self, metric: str) -> Any:
        """Collect specific metric value"""
        try:
            if metric == "cpu_percent":
                return psutil.cpu_percent(interval=1)
            elif metric == "memory_percent":
                return psutil.virtual_memory().percent
            elif metric == "disk_usage":
                return psutil.disk_usage('/').percent
            elif metric == "network_io":
                return {
                    "bytes_sent": psutil.net_io_counters().bytes_sent,
                    "bytes_recv": psutil.net_io_counters().bytes_recv
                }
            elif metric == "process_count":
                return len(psutil.pids())
            elif metric == "thread_count":
                return sum(p.num_threads() for p in psutil.process_iter(['num_threads']))
            else:
                raise ValueError(f"Unknown metric: {metric}")

        except Exception as e:
            logger.error(f"Metric collection failed: {str(e)}")
            raise

    async def _handle_metric_update(self, message: ProcessingMessage) -> None:
        """Handle metric update"""
        monitoring_id = message.content.get('monitoring_id')
        metric = message.content.get('metric')
        value = message.content.get('value')
        context = self.active_contexts.get(monitoring_id)

        if not context:
            return

        try:
            # Update context
            context.metrics.__dict__[metric] = value
            context.updated_at = datetime.now()

            # Check thresholds
            if metric in context.config['thresholds']:
                await self._check_metric_threshold(monitoring_id, metric, value)

        except Exception as e:
            logger.error(f"Metric update failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _check_metric_threshold(self, monitoring_id: str, metric: str, value: float) -> None:
        """Check metric against threshold"""
        try:
            context = self.active_contexts.get(monitoring_id)
            if not context or metric not in context.config['thresholds']:
                return

            threshold = context.config['thresholds'][metric]
            if value >= threshold['warning'] and value < threshold['critical']:
                await self._handle_threshold_violation(monitoring_id, metric, value, 'warning')
            elif value >= threshold['critical']:
                await self._handle_threshold_violation(monitoring_id, metric, value, 'critical')

        except Exception as e:
            logger.error(f"Threshold check failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _handle_metric_alert(self, message: ProcessingMessage) -> None:
        """Handle metric alert"""
        monitoring_id = message.content.get('monitoring_id')
        alert = message.content.get('alert')
        context = self.active_contexts.get(monitoring_id)

        if not context:
            return

        try:
            # Store alert
            if monitoring_id not in self.alert_history:
                self.alert_history[monitoring_id] = []
            self.alert_history[monitoring_id].append(alert)

            # Publish alert
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_CREATE,
                    content={
                        'monitoring_id': monitoring_id,
                        'alert': alert
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="alert_service"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Metric alert handling failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _handle_threshold_update(self, message: ProcessingMessage) -> None:
        """Handle threshold update request"""
        monitoring_id = message.content.get('monitoring_id')
        thresholds = message.content.get('thresholds', {})
        context = self.active_contexts.get(monitoring_id)

        if not context:
            return

        try:
            # Update thresholds
            context.config['thresholds'].update(thresholds)
            context.updated_at = datetime.now()

            # Publish update confirmation
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_THRESHOLD_UPDATED,
                    content={
                        'monitoring_id': monitoring_id,
                        'thresholds': thresholds
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="monitoring_service"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Threshold update failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _handle_alert_create(self, message: ProcessingMessage) -> None:
        """Handle alert creation"""
        monitoring_id = message.content.get('monitoring_id')
        alert = message.content.get('alert')
        context = self.active_contexts.get(monitoring_id)

        if not context:
            return

        try:
            # Store alert
            if monitoring_id not in self.alert_history:
                self.alert_history[monitoring_id] = []
            self.alert_history[monitoring_id].append(alert)

            # Publish alert
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_CREATED,
                    content={
                        'monitoring_id': monitoring_id,
                        'alert': alert
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="alert_service"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Alert creation failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _handle_alert_resolve(self, message: ProcessingMessage) -> None:
        """Handle alert resolution"""
        monitoring_id = message.content.get('monitoring_id')
        alert_id = message.content.get('alert_id')
        context = self.active_contexts.get(monitoring_id)

        if not context:
            return

        try:
            # Update alert status
            for alert in self.alert_history.get(monitoring_id, []):
                if alert['alert_id'] == alert_id:
                    alert['status'] = 'resolved'
                    alert['resolved_at'] = datetime.now().isoformat()
                    break

            # Publish resolution
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_RESOLVED,
                    content={
                        'monitoring_id': monitoring_id,
                        'alert_id': alert_id
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="alert_service"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Alert resolution failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _handle_alert_acknowledge(self, message: ProcessingMessage) -> None:
        """Handle alert acknowledgment"""
        monitoring_id = message.content.get('monitoring_id')
        alert_id = message.content.get('alert_id')
        context = self.active_contexts.get(monitoring_id)

        if not context:
            return

        try:
            # Update alert status
            for alert in self.alert_history.get(monitoring_id, []):
                if alert['alert_id'] == alert_id:
                    alert['status'] = 'acknowledged'
                    alert['acknowledged_at'] = datetime.now().isoformat()
                    break

            # Publish acknowledgment
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_ACKNOWLEDGED,
                    content={
                        'monitoring_id': monitoring_id,
                        'alert_id': alert_id
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="alert_service"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Alert acknowledgment failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _handle_resource_request(self, message: ProcessingMessage) -> None:
        """Handle resource request"""
        monitoring_id = message.content.get('monitoring_id')
        resource_config = message.content.get('resource_config', {})
        context = self.active_contexts.get(monitoring_id)

        if not context:
            return

        try:
            # Check resource availability
            if not await self._check_resource_availability(resource_config):
                await self._handle_resource_unavailable(monitoring_id, 'Requested resources not available')
                return

            # Allocate resources
            context.resource_allocation.update(resource_config)
            context.updated_at = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_RESOURCE_ALLOCATED,
                    content={
                        'monitoring_id': monitoring_id,
                        'allocated_resources': resource_config
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="resource_manager"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Resource request failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _handle_resource_release(self, message: ProcessingMessage) -> None:
        """Handle resource release"""
        monitoring_id = message.content.get('monitoring_id')
        resources = message.content.get('resources', [])
        context = self.active_contexts.get(monitoring_id)

        if not context:
            return

        try:
            # Release resources
            for resource in resources:
                context.resource_allocation.pop(resource, None)

            context.updated_at = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_RESOURCE_RELEASED,
                    content={
                        'monitoring_id': monitoring_id,
                        'released_resources': resources
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="resource_manager"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Resource release failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _handle_health_check(self, message: ProcessingMessage) -> None:
        """Handle health check request"""
        monitoring_id = message.content.get('monitoring_id')
        context = self.active_contexts.get(monitoring_id)

        if not context:
            return

        try:
            # Collect health metrics
            health_metrics = {
                'state': context.state.value,
                'process_duration': (datetime.now() - context.created_at).total_seconds(),
                'resource_usage': await self._collect_resource_metrics(),
                'alert_count': len(self.alert_history.get(monitoring_id, [])),
                'metric_count': len(context.metrics.__dict__)
            }

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_HEALTH_STATUS,
                    content={
                        'monitoring_id': monitoring_id,
                        'health_metrics': health_metrics
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="monitoring_service"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _handle_config_update(self, message: ProcessingMessage) -> None:
        """Handle configuration update"""
        monitoring_id = message.content.get('monitoring_id')
        config_updates = message.content.get('config', {})
        context = self.active_contexts.get(monitoring_id)

        if not context:
            return

        try:
            # Update configuration
            context.config.update(config_updates)
            context.updated_at = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_CONFIG_UPDATED,
                    content={
                        'monitoring_id': monitoring_id,
                        'config': config_updates
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="monitoring_service"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Config update failed: {str(e)}")
            await self._handle_error(monitoring_id, str(e))

    async def _cleanup_monitoring(self, monitoring_id: str) -> None:
        """Clean up monitoring resources"""
        try:
            # Clean up context
            self.active_contexts.pop(monitoring_id, None)
            
            # Clean up history
            self.metric_history.pop(monitoring_id, None)
            self.alert_history.pop(monitoring_id, None)
            self.last_alert_time.pop(monitoring_id, None)

            logger.info(f"Cleaned up monitoring resources for {monitoring_id}")

        except Exception as e:
            logger.error(f"Monitoring cleanup failed: {str(e)}")

    async def _handle_error(self, monitoring_id: str, error: str) -> None:
        """Handle monitoring errors"""
        try:
            context = self.active_contexts.get(monitoring_id)
            if context:
                context.state = MonitoringState.ERROR
                context.error = error
                context.updated_at = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_FAILED,
                    content={
                        'monitoring_id': monitoring_id,
                        'error': error,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="monitoring_service"
                    )
                )
            )

            await self._cleanup_monitoring(monitoring_id)

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")