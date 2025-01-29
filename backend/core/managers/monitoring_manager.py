import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import asyncio

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    MonitoringContext,
    MonitoringState,
    ManagerState,
    ComponentType,
    ModuleIdentifier
)
from .base.base_manager import BaseManager

logger = logging.getLogger(__name__)


class MonitoringManager(BaseManager):
    """Enhanced Monitoring Manager for system-wide monitoring and metrics collection"""

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

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name=component_name,
            component_type=ComponentType.MONITORING_MANAGER,
            department=domain_type,
            role="manager"
        )

        # Active monitoring processes
        self.active_processes: Dict[str, MonitoringContext] = {}

        # Monitoring configuration
        self.collection_intervals: Dict[str, int] = {}
        self.alert_thresholds: Dict[str, Dict[str, float]] = {
            "cpu_usage": {"warning": 80, "critical": 95},
            "memory_usage": {"warning": 85, "critical": 95},
            "disk_space": {"warning": 80, "critical": 90},
            "latency_ms": {"warning": 1000, "critical": 5000}
        }

    async def _setup_domain_handlers(self) -> None:
        """Initialize monitoring-specific message handlers"""
        handlers = {
            # Core monitoring flow
            MessageType.MONITORING_PROCESS_START: self._handle_monitoring_start,
            MessageType.MONITORING_PROCESS_PROGRESS: self._handle_monitoring_progress,
            MessageType.MONITORING_PROCESS_COMPLETE: self._handle_monitoring_complete,
            MessageType.MONITORING_PROCESS_FAILED: self._handle_monitoring_failed,

            # Metrics handling
            MessageType.MONITORING_METRICS_COLLECT: self._handle_metrics_collect,
            MessageType.MONITORING_METRICS_UPDATE: self._handle_metrics_update,
            MessageType.MONITORING_METRICS_AGGREGATE: self._handle_metrics_aggregate,
            MessageType.MONITORING_METRICS_EXPORT: self._handle_metrics_export,

            # Performance monitoring
            MessageType.MONITORING_PERFORMANCE_CHECK: self._handle_performance_check,
            MessageType.MONITORING_PERFORMANCE_ALERT: self._handle_performance_alert,
            MessageType.MONITORING_PERFORMANCE_REPORT: self._handle_performance_report,

            # Resource monitoring
            MessageType.MONITORING_RESOURCE_CHECK: self._handle_resource_check,
            MessageType.MONITORING_RESOURCE_ALERT: self._handle_resource_alert,
            MessageType.MONITORING_RESOURCE_THRESHOLD: self._handle_resource_threshold,

            # Health monitoring
            MessageType.MONITORING_HEALTH_CHECK: self._handle_health_check,
            MessageType.MONITORING_HEALTH_STATUS: self._handle_health_status,
            MessageType.MONITORING_HEALTH_ALERT: self._handle_health_alert,

            # Alert management
            MessageType.MONITORING_ALERT_GENERATE: self._handle_alert_generate,
            MessageType.MONITORING_ALERT_PROCESS: self._handle_alert_process,
            MessageType.MONITORING_ALERT_RESOLVE: self._handle_alert_resolve,
            MessageType.MONITORING_ALERT_ESCALATE: self._handle_alert_escalate,

            # Export handling
            MessageType.MONITORING_EXPORT_PROMETHEUS: self._handle_prometheus_export,
            MessageType.MONITORING_EXPORT_INFLUXDB: self._handle_influxdb_export,
            MessageType.MONITORING_EXPORT_JSON: self._handle_json_export,

            # System operations
            MessageType.MONITORING_CONFIG_UPDATE: self._handle_config_update,
            MessageType.MONITORING_CLEANUP_REQUEST: self._handle_cleanup_request,
            MessageType.MONITORING_BACKUP_REQUEST: self._handle_backup_request
        }

        for message_type, handler in handlers.items():
            await self.register_message_handler(message_type, handler)

    async def request_monitoring(self, pipeline_id: str, config: Dict[str, Any]) -> str:
        """Initialize a new monitoring process"""
        try:
            # Create monitoring context
            context = MonitoringContext(
                pipeline_id=pipeline_id,
                correlation_id=str(uuid.uuid4()),
                monitor_state=MonitoringState.INITIALIZING,
                metric_types=config.get('metric_types', []),
                collectors_enabled=config.get('collectors', []),
                collection_interval=config.get('interval', 60)
            )

            self.active_processes[pipeline_id] = context

            # Request monitoring start
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESS_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        domain_type="monitoring",
                        processing_stage=ProcessingStage.INITIAL_VALIDATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

            logger.info(f"Monitoring initiated for pipeline: {pipeline_id}")
            return context.correlation_id

        except Exception as e:
            logger.error(f"Failed to initiate monitoring: {str(e)}")
            raise

    async def _handle_monitoring_start(self, message: ProcessingMessage) -> None:
        """Handle monitoring process start"""
        pipeline_id = message.content.get("pipeline_id")
        config = message.content.get("config", {})

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Initialize collectors
            for collector in context.collectors_enabled:
                await self._initialize_collector(collector, config)

            # Start collection interval
            self.collection_intervals[pipeline_id] = asyncio.create_task(
                self._collect_metrics_interval(pipeline_id, context.collection_interval)
            )

            context.monitor_state = MonitoringState.COLLECTING
            await self._notify_state_change(pipeline_id, context)

        except Exception as e:
            logger.error(f"Monitoring start failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_metrics_collect(self, message: ProcessingMessage) -> None:
        """Handle metrics collection request"""
        pipeline_id = message.content.get("pipeline_id")
        metrics_type = message.content.get("metrics_type")

        try:
            # Collect metrics based on type
            metrics = await self._collect_system_metrics(metrics_type)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_METRICS_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'metrics': metrics,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Metrics collection failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _collect_system_metrics(self, metrics_type: str) -> Dict[str, Any]:
        """Collect system metrics based on type"""
        try:
            import psutil

            if metrics_type == "system":
                return {
                    'cpu_usage': psutil.cpu_percent(),
                    'memory_usage': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/').percent,
                    'network_connections': len(psutil.net_connections())
                }
            elif metrics_type == "process":
                process = psutil.Process()
                return {
                    'process_cpu': process.cpu_percent(),
                    'process_memory': process.memory_percent(),
                    'open_files': len(process.open_files()),
                    'threads': process.num_threads()
                }
            else:
                raise ValueError(f"Unsupported metrics type: {metrics_type}")

        except Exception as e:
            logger.error(f"System metrics collection failed: {str(e)}")
            return {}

    async def _handle_alert_generate(self, message: ProcessingMessage) -> None:
        """Handle alert generation"""
        pipeline_id = message.content.get("pipeline_id")
        alert_data = message.content.get("alert", {})

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Process alert
            severity = self._determine_alert_severity(alert_data)
            if severity in ["critical", "high"]:
                await self._handle_high_priority_alert(pipeline_id, alert_data, severity)
            else:
                await self._handle_standard_alert(pipeline_id, alert_data, severity)

        except Exception as e:
            logger.error(f"Alert generation failed: {str(e)}")

    async def _handle_resource_threshold(self, message: ProcessingMessage) -> None:
        """Handle resource threshold breaches"""
        pipeline_id = message.content.get("pipeline_id")
        threshold_data = message.content.get("threshold", {})

        try:
            # Check threshold type and severity
            resource_type = threshold_data.get("resource_type")
            current_value = threshold_data.get("current_value")

            if resource_type and current_value:
                thresholds = self.alert_thresholds.get(resource_type, {})

                if current_value >= thresholds.get("critical", float('inf')):
                    await self._handle_critical_threshold_breach(pipeline_id, threshold_data)
                elif current_value >= thresholds.get("warning", float('inf')):
                    await self._handle_warning_threshold_breach(pipeline_id, threshold_data)

        except Exception as e:
            logger.error(f"Threshold handling failed: {str(e)}")

    async def _handle_performance_check(self, message: ProcessingMessage) -> None:
        """Handle performance check requests"""
        pipeline_id = message.content.get("pipeline_id")
        check_type = message.content.get("check_type")

        try:
            # Collect performance metrics
            performance_data = await self._collect_performance_metrics(check_type)

            # Analyze performance
            issues = self._analyze_performance(performance_data)

            if issues:
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.MONITORING_PERFORMANCE_ALERT,
                        content={
                            'pipeline_id': pipeline_id,
                            'issues': issues,
                            'performance_data': performance_data
                        },
                        source_identifier=self.module_identifier
                    )
                )

        except Exception as e:
            logger.error(f"Performance check failed: {str(e)}")

    async def _collect_performance_metrics(self, check_type: str) -> Dict[str, Any]:
        """Collect performance metrics based on type"""
        try:
            if check_type == "system":
                return await self._collect_system_performance()
            elif check_type == "application":
                return await self._collect_application_performance()
            elif check_type == "network":
                return await self._collect_network_performance()
            else:
                raise ValueError(f"Unsupported check type: {check_type}")

        except Exception as e:
            logger.error(f"Performance metrics collection failed: {str(e)}")
            return {}

    def _analyze_performance(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze performance data for issues"""
        issues = []

        # CPU analysis
        if cpu_usage := performance_data.get('cpu_usage'):
            if cpu_usage > 90:
                issues.append({
                    'type': 'cpu',
                    'severity': 'critical',
                    'message': f'CPU usage critically high: {cpu_usage}%'
                })
            elif cpu_usage > 80:
                issues.append({
                    'type': 'cpu',
                    'severity': 'warning',
                    'message': f'CPU usage high: {cpu_usage}%'
                })

        # Memory analysis
        if mem_usage := performance_data.get('memory_usage'):
            if mem_usage > 90:
                issues.append({
                    'type': 'memory',
                    'severity': 'critical',
                    'message': f'Memory usage critically high: {mem_usage}%'
                })
            elif mem_usage > 80:
                issues.append({
                    'type': 'memory',
                    'severity': 'warning',
                    'message': f'Memory usage high: {mem_usage}%'
                })

        return issues

    async def _handle_health_check(self, message: ProcessingMessage) -> None:
        """Handle health check requests"""
        pipeline_id = message.content.get("pipeline_id")

        try:
            # Perform health checks
            health_status = await self._check_system_health()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_HEALTH_STATUS,
                    content={
                        'pipeline_id': pipeline_id,
                        'health_status': health_status,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

            # Check for health issues
            if not health_status.get('healthy', False):
                await self._handle_health_issues(pipeline_id, health_status)

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")

    async def _export_metrics(self, format_type: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Export metrics in specified format"""
        if format_type == "prometheus":
            return await self._export_prometheus_format(metrics)
        elif format_type == "influxdb":
            return await self._export_influxdb_format(metrics)
        else:
            return await self._export_json_format(metrics)

    async def _export_prometheus_format(self, metrics: Dict[str, Any]) -> str:
        """Export metrics in Prometheus format"""
        output = []
        timestamp = int(datetime.now().timestamp() * 1000)

        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)):
                output.append(f"{metric_name} {value} {timestamp}")

        return "\n".join(output)

    async def _export_influxdb_format(self, metrics: Dict[str, Any]) -> str:
        """Export metrics in InfluxDB line protocol format"""
        output = []
        timestamp = int(datetime.now().timestamp() * 1000000000)  # nanoseconds

        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)):
                output.append(f"system_metrics,metric={metric_name} value={value} {timestamp}")

        return "\n".join(output)

    async def _export_json_format(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Export metrics in JSON format"""
        return {
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'metadata': {
                'version': '1.0',
                'source': self.module_identifier.component_name
            }
        }

    async def _handle_metrics_aggregate(self, message: ProcessingMessage) -> None:
        """Handle metrics aggregation requests"""
        pipeline_id = message.content.get("pipeline_id")
        metric_names = message.content.get("metrics", [])

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Aggregate specified metrics
            aggregated = {}
            for metric in metric_names:
                values = [
                    m.get(metric)
                    for m in context.collected_metrics.values()
                    if isinstance(m.get(metric), (int, float))
                ]

                if values:
                    aggregated[metric] = {
                        'avg': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'count': len(values)
                    }

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_METRICS_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'aggregated_metrics': aggregated,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Metrics aggregation failed: {str(e)}")

    async def _handle_backup_request(self, message: ProcessingMessage) -> None:
        """Handle monitoring data backup requests"""
        pipeline_id = message.content.get("pipeline_id")
        backup_type = message.content.get("backup_type", "full")

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Create backup based on type
            if backup_type == "full":
                backup_data = {
                    'metrics': context.collected_metrics,
                    'aggregates': context.aggregated_metrics,
                    'alerts': context.active_alerts,
                    'timestamp': datetime.now().isoformat()
                }
            else:  # incremental
                backup_data = {
                    'metrics': context.collected_metrics,
                    'timestamp': datetime.now().isoformat()
                }

            # Store backup
            await self._store_backup(pipeline_id, backup_data)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_BACKUP_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'backup_id': str(uuid.uuid4()),
                        'backup_type': backup_type,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Backup creation failed: {str(e)}")

    async def _store_backup(self, pipeline_id: str, backup_data: Dict[str, Any]) -> None:
        """Store monitoring backup data"""
        try:
            # Implementation would depend on storage backend
            # For example, could store in filesystem, database, or cloud storage
            pass
        except Exception as e:
            logger.error(f"Backup storage failed: {str(e)}")

    async def _check_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive system health check"""
        try:
            # System metrics
            system_health = await self._collect_system_metrics("system")

            # Component health
            component_health = {
                component: await self._check_component_health(component)
                for component in self.active_processes.keys()
            }

            # Resource health
            resource_health = await self._check_resource_health()

            # Determine overall health
            is_healthy = all([
                all(system_health.values()),
                all(component_health.values()),
                all(resource_health.values())
            ])

            return {
                'healthy': is_healthy,
                'system': system_health,
                'components': component_health,
                'resources': resource_health,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {'healthy': False, 'error': str(e)}

    async def _check_component_health(self, component_id: str) -> Dict[str, bool]:
        """Check health of specific component"""
        try:
            # Check component responsiveness
            is_responsive = await self._ping_component(component_id)

            # Check component metrics
            metrics = await self._collect_component_metrics(component_id)
            metrics_healthy = all(
                value < threshold
                for value, threshold in self.alert_thresholds.items()
            )

            return {
                'responsive': is_responsive,
                'metrics_healthy': metrics_healthy
            }

        except Exception as e:
            logger.error(f"Component health check failed: {str(e)}")
            return {'responsive': False, 'metrics_healthy': False}

    async def _check_resource_health(self) -> Dict[str, bool]:
        """Check health of system resources"""
        try:
            import psutil

            # Get resource usage
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                'cpu_healthy': cpu_usage < self.alert_thresholds['cpu_usage']['warning'],
                'memory_healthy': memory.percent < self.alert_thresholds['memory_usage']['warning'],
                'disk_healthy': disk.percent < self.alert_thresholds['disk_space']['warning']
            }

        except Exception as e:
            logger.error(f"Resource health check failed: {str(e)}")
            return {
                'cpu_healthy': False,
                'memory_healthy': False,
                'disk_healthy': False
            }

    async def _handle_alert_escalate(self, message: ProcessingMessage) -> None:
        """Handle alert escalation"""
        pipeline_id = message.content.get("pipeline_id")
        alert = message.content.get("alert", {})

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Update alert severity
            alert['severity'] = 'critical'
            alert['escalated_at'] = datetime.now().isoformat()

            # Notify about escalation
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_GENERATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'alert': alert,
                        'escalated': True
                    },
                    source_identifier=self.module_identifier
                )
            )

            # Trigger emergency procedures if needed
            if alert.get('type') in ['system_failure', 'security_breach']:
                await self._trigger_emergency_procedures(pipeline_id, alert)

        except Exception as e:
            logger.error(f"Alert escalation failed: {str(e)}")

    async def _handle_config_update(self, message: ProcessingMessage) -> None:
        """Handle monitoring configuration updates"""
        pipeline_id = message.content.get("pipeline_id")
        config_updates = message.content.get("config", {})

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Update thresholds if provided
            if thresholds := config_updates.get('thresholds'):
                self.alert_thresholds.update(thresholds)

            # Update collection interval if provided
            if interval := config_updates.get('collection_interval'):
                context.collection_interval = interval

                # Restart collection if needed
                if pipeline_id in self.collection_intervals:
                    self.collection_intervals[pipeline_id].cancel()
                    self.collection_intervals[pipeline_id] = asyncio.create_task(
                        self._collect_metrics_interval(pipeline_id, interval)
                    )

            # Update other context configurations
            context.metric_types = config_updates.get('metric_types', context.metric_types)
            context.collectors_enabled = config_updates.get('collectors', context.collectors_enabled)

            await self._notify_config_update(pipeline_id, config_updates)

        except Exception as e:
            logger.error(f"Configuration update failed: {str(e)}")

    async def _notify_config_update(self, pipeline_id: str, updates: Dict[str, Any]) -> None:
        """Notify about configuration updates"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.MONITORING_CONFIG_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'updates': updates,
                    'timestamp': datetime.now().isoformat()
                },
                source_identifier=self.module_identifier
            )
        )

    async def _ping_component(self, component_id: str) -> bool:
        """Check if component is responsive"""
        try:
            response = await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_HEALTH_CHECK,
                    content={'timestamp': datetime.now().isoformat()},
                    target_identifier=ModuleIdentifier(
                        component_name=component_id,
                        component_type=ComponentType.CORE
                    ),
                    source_identifier=self.module_identifier
                )
            )
            return response is not None
        except Exception:
            return False

    async def _trigger_emergency_procedures(self, pipeline_id: str, alert: Dict[str, Any]) -> None:
        """Handle emergency situations"""
        try:
            # Stop all non-essential processes
            await self._stop_non_essential_processes()

            # Save system state
            await self._save_system_state(pipeline_id)

            # Notify emergency contacts
            await self._notify_emergency_contacts(alert)

        except Exception as e:
            logger.error(f"Emergency procedures failed: {str(e)}")

    async def _collect_metrics_interval(self, pipeline_id: str, interval: int) -> None:
        """Continuously collect metrics at specified interval"""
        try:
            while True:
                metrics = await self._collect_system_metrics("system")

                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.MONITORING_METRICS_UPDATE,
                        content={
                            'pipeline_id': pipeline_id,
                            'metrics': metrics,
                            'timestamp': datetime.now().isoformat()
                        },
                        source_identifier=self.module_identifier
                    )
                )

                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            logger.info(f"Metrics collection stopped for pipeline: {pipeline_id}")
        except Exception as e:
            logger.error(f"Metrics collection failed: {str(e)}")