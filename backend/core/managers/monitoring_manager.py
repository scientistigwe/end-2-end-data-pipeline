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

    class MonitoringManager(BaseManager):
        """Enhanced Monitoring Manager for system-wide monitoring and metrics collection"""

        def __init__(
                self,
                message_broker: MessageBroker,
                component_name: str = "monitoring_manager",
                domain_type: str = "monitoring"
        ):
            # Call base class initialization first
            super().__init__(
                message_broker=message_broker,
                component_name=component_name,
                domain_type=domain_type
            )

            # Active processes and contexts
            self.active_processes: Dict[str, MonitoringContext] = {}

            # Monitoring configuration and thresholds
            self.monitoring_thresholds = {
                "alert_thresholds": {
                    "cpu_usage": {"warning": 80, "critical": 95},
                    "memory_usage": {"warning": 85, "critical": 95},
                    "disk_space": {"warning": 80, "critical": 90},
                    "latency_ms": {"warning": 1000, "critical": 5000}
                },
                "collection_interval": 60,  # seconds
                "max_processing_time": 3600  # 1 hour
            }

        async def _initialize_manager(self) -> None:
            """Initialize monitoring manager components"""
            try:
                # Initialize base components - this will also start background tasks
                await super()._initialize_manager()

                # Setup monitoring-specific message handlers
                await self._setup_domain_handlers()

                # Update state
                self.state = ManagerState.ACTIVE
                logger.info(f"Monitoring manager initialized successfully: {self.context.component_name}")

            except Exception as e:
                logger.error(f"Failed to initialize monitoring manager: {str(e)}")
                self.state = ManagerState.ERROR
                raise

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

    async def _handle_metrics_export(self, message: ProcessingMessage) -> None:
        """
        Handle metrics export request

        Handles exporting collected metrics in various formats like Prometheus, InfluxDB, or JSON

        Args:
            message (ProcessingMessage): Processing message containing export details
        """
        pipeline_id = message.content.get("pipeline_id")
        export_format = message.content.get("format", "json")

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                logger.warning(f"No monitoring context found for pipeline: {pipeline_id}")
                return

            # Collect metrics to export (prefer aggregated if available)
            metrics_to_export = (
                context.aggregated_metrics
                if context.aggregated_metrics
                else context.collected_metrics
            )

            # If no metrics are available, log a warning and return
            if not metrics_to_export:
                logger.warning(f"No metrics available to export for pipeline: {pipeline_id}")
                return

            # Export metrics in the specified format
            exported_metrics = await self._export_metrics(export_format, metrics_to_export)

            # Publish exported metrics
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_METRICS_EXPORT_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'export_format': export_format,
                        'exported_metrics': exported_metrics,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Metrics export failed: {str(e)}")

            # Publish error message
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_METRICS_EXPORT_FAILED,
                    content={
                        'pipeline_id': pipeline_id,
                        'export_format': export_format,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )


    async def _handle_monitoring_progress(self, message: ProcessingMessage) -> None:
        """Handle monitoring progress updates"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            progress = message.content.get('progress', 0)
            context.progress = progress
            context.updated_at = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESS_PROGRESS,
                    content={
                        'pipeline_id': pipeline_id,
                        'progress': progress,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="monitoring_service",
                        domain_type="monitoring"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Progress update failed: {str(e)}")

    async def _handle_monitoring_complete(self, message: ProcessingMessage) -> None:
        """Handle monitoring process completion"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.monitor_state = MonitoringState.COMPLETED
            context.completed_at = datetime.now()

            # Stop collection interval if exists
            if pipeline_id in self.collection_intervals:
                self.collection_intervals[pipeline_id].cancel()
                del self.collection_intervals[pipeline_id]

            # Publish final metrics
            await self._publish_final_metrics(pipeline_id)

            # Cleanup process
            await self._cleanup_monitoring_process(pipeline_id)

        except Exception as e:
            logger.error(f"Monitoring completion failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_monitoring_failed(self, message: ProcessingMessage) -> None:
        """Handle monitoring process failure"""
        pipeline_id = message.content.get('pipeline_id')
        error = message.content.get('error', 'Unknown error')

        try:
            context = self.active_processes.get(pipeline_id)
            if context:
                # Update context state
                context.monitor_state = MonitoringState.FAILED
                context.error = error

                # Stop collection interval if exists
                if pipeline_id in self.collection_intervals:
                    self.collection_intervals[pipeline_id].cancel()
                    del self.collection_intervals[pipeline_id]

                # Notify about failure
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.MONITORING_PROCESS_FAILED,
                        content={
                            'pipeline_id': pipeline_id,
                            'error': error,
                            'timestamp': datetime.now().isoformat()
                        },
                        metadata=MessageMetadata(
                            correlation_id=context.correlation_id,
                            source_component=self.context.component_name,
                            target_component="control_point_manager",
                            domain_type="monitoring"
                        )
                    )
                )

                # Cleanup process
                await self._cleanup_monitoring_process(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle monitoring failure: {str(e)}")

    async def _handle_metrics_update(self, message: ProcessingMessage) -> None:
        """Handle metrics updates"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            metrics = message.content.get('metrics', {})

            # Store metrics
            context.collected_metrics[datetime.now().isoformat()] = metrics

            # Check thresholds
            await self._check_metric_thresholds(pipeline_id, metrics)

        except Exception as e:
            logger.error(f"Metrics update failed: {str(e)}")

    async def _handle_cleanup_request(self, message: ProcessingMessage) -> None:
        """Handle cleanup request for monitoring resources"""
        pipeline_id = message.content.get('pipeline_id')

        try:
            await self._cleanup_monitoring_process(pipeline_id)
            logger.info(f"Monitoring cleanup completed for pipeline: {pipeline_id}")

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")

    async def _cleanup_monitoring_process(self, pipeline_id: str) -> None:
        """Clean up monitoring process resources"""
        try:
            # Stop metric collection
            if pipeline_id in self.collection_intervals:
                self.collection_intervals[pipeline_id].cancel()
                del self.collection_intervals[pipeline_id]

            # Remove from active processes
            if pipeline_id in self.active_processes:
                del self.active_processes[pipeline_id]

            # Clear any cached data
            await self._clear_monitoring_cache(pipeline_id)

        except Exception as e:
            logger.error(f"Process cleanup failed: {str(e)}")
            raise

    async def _check_metric_thresholds(self, pipeline_id: str, metrics: Dict[str, Any]) -> None:
        """Check metrics against defined thresholds"""
        for metric_name, value in metrics.items():
            if metric_name in self.monitoring_thresholds["alert_thresholds"]:
                thresholds = self.monitoring_thresholds["alert_thresholds"][metric_name]

                if value >= thresholds["critical"]:
                    await self._handle_critical_threshold_breach(pipeline_id, metric_name, value)
                elif value >= thresholds["warning"]:
                    await self._handle_warning_threshold_breach(pipeline_id, metric_name, value)

    async def _clear_monitoring_cache(self, pipeline_id: str) -> None:
        """Clear cached monitoring data"""
        try:
            context = self.active_processes.get(pipeline_id)
            if context:
                context.collected_metrics.clear()
                context.aggregated_metrics.clear()
                context.active_alerts.clear()

        except Exception as e:
            logger.error(f"Cache clearing failed: {str(e)}")

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

    async def _handle_performance_alert(self, message: ProcessingMessage) -> None:
        """Handle performance alert events"""
        pipeline_id = message.content.get("pipeline_id")
        performance_data = message.content.get("performance_data", {})
        issues = message.content.get("issues", [])

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Record alert in context
            alert = {
                'type': 'performance',
                'timestamp': datetime.now().isoformat(),
                'issues': issues,
                'data': performance_data
            }

            context.active_alerts[str(uuid.uuid4())] = alert

            # Determine severity based on issues
            severity = self._determine_performance_severity(issues)

            # Handle based on severity
            if severity == 'critical':
                await self._handle_critical_performance(pipeline_id, alert)
            else:
                await self._notify_performance_issue(pipeline_id, alert)

        except Exception as e:
            logger.error(f"Performance alert handling failed: {str(e)}")


    async def _handle_performance_report(self, message: ProcessingMessage) -> None:
        """Handle performance report generation requests"""
        pipeline_id = message.content.get("pipeline_id")
        report_type = message.content.get("report_type", "summary")

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Generate performance report
            report_data = await self._generate_performance_report(
                context, report_type
            )

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PERFORMANCE_REPORT,
                    content={
                        'pipeline_id': pipeline_id,
                        'report': report_data,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Performance report generation failed: {str(e)}")


    async def _handle_resource_alert(self, message: ProcessingMessage) -> None:
        """Handle resource-related alerts"""
        pipeline_id = message.content.get("pipeline_id")
        resource_data = message.content.get("resource_data", {})

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Create resource alert
            alert = {
                'type': 'resource',
                'timestamp': datetime.now().isoformat(),
                'resource_type': resource_data.get('type'),
                'current_value': resource_data.get('value'),
                'threshold': resource_data.get('threshold')
            }

            alert_id = str(uuid.uuid4())
            context.active_alerts[alert_id] = alert

            # Determine if immediate action needed
            if self._requires_immediate_action(resource_data):
                await self._handle_critical_resource_alert(pipeline_id, alert)
            else:
                await self._notify_resource_alert(pipeline_id, alert)

        except Exception as e:
            logger.error(f"Resource alert handling failed: {str(e)}")


    async def _handle_health_alert(self, message: ProcessingMessage) -> None:
        """Handle health-related alerts"""
        pipeline_id = message.content.get("pipeline_id")
        health_data = message.content.get("health_data", {})

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Create health alert
            alert = {
                'type': 'health',
                'timestamp': datetime.now().isoformat(),
                'status': health_data.get('status'),
                'issues': health_data.get('issues', []),
                'components': health_data.get('affected_components', [])
            }

            alert_id = str(uuid.uuid4())
            context.active_alerts[alert_id] = alert

            # Handle based on health status
            if health_data.get('status') == 'critical':
                await self._handle_critical_health_alert(pipeline_id, alert)
            else:
                await self._notify_health_alert(pipeline_id, alert)

        except Exception as e:
            logger.error(f"Health alert handling failed: {str(e)}")


    async def _handle_alert_resolve(self, message: ProcessingMessage) -> None:
        """Handle alert resolution"""
        pipeline_id = message.content.get("pipeline_id")
        alert_id = message.content.get("alert_id")
        resolution_data = message.content.get("resolution", {})

        try:
            context = self.active_processes.get(pipeline_id)
            if not context or alert_id not in context.active_alerts:
                return

            # Update alert with resolution
            alert = context.active_alerts[alert_id]
            alert['resolved'] = True
            alert['resolved_at'] = datetime.now().isoformat()
            alert['resolution'] = resolution_data

            # Remove from active alerts
            del context.active_alerts[alert_id]

            # Notify about resolution
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_RESOLVED,
                    content={
                        'pipeline_id': pipeline_id,
                        'alert_id': alert_id,
                        'resolution': resolution_data,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Alert resolution failed: {str(e)}")


    async def _handle_alert_process(self, message: ProcessingMessage) -> None:
        """Handle alert processing"""
        pipeline_id = message.content.get("pipeline_id")
        alert_id = message.content.get("alert_id")
        process_data = message.content.get("process_data", {})

        try:
            context = self.active_processes.get(pipeline_id)
            if not context or alert_id not in context.active_alerts:
                return

            alert = context.active_alerts[alert_id]

            # Update alert processing status
            alert['processing_status'] = process_data.get('status')
            alert['last_processed'] = datetime.now().isoformat()
            alert['processing_details'] = process_data.get('details', {})

            # Handle based on processing result
            if process_data.get('status') == 'requires_escalation':
                await self._handle_alert_escalate(message)
            elif process_data.get('status') == 'resolved':
                await self._handle_alert_resolve(message)
            else:
                await self._notify_alert_status(pipeline_id, alert_id, alert)

        except Exception as e:
            logger.error(f"Alert processing failed: {str(e)}")


    # Helper methods for the handlers above

    def _determine_performance_severity(self, issues: List[Dict[str, Any]]) -> str:
        """Determine severity level based on performance issues"""
        if any(issue.get('severity') == 'critical' for issue in issues):
            return 'critical'
        elif any(issue.get('severity') == 'high' for issue in issues):
            return 'high'
        return 'warning'


    async def _generate_performance_report(
            self,
            context: MonitoringContext,
            report_type: str
    ) -> Dict[str, Any]:
        """Generate performance report based on type"""
        if report_type == "summary":
            return self._generate_summary_report(context)
        elif report_type == "detailed":
            return await self._generate_detailed_report(context)
        else:
            return self._generate_basic_report(context)


    def _requires_immediate_action(self, resource_data: Dict[str, Any]) -> bool:
        """Determine if resource alert requires immediate action"""
        if resource_type := resource_data.get('type'):
            current_value = resource_data.get('value', 0)
            thresholds = self.monitoring_thresholds['alert_thresholds'].get(resource_type, {})
            return current_value >= thresholds.get('critical', float('inf'))
        return False


    async def _handle_critical_performance(
            self,
            pipeline_id: str,
            alert: Dict[str, Any]
    ) -> None:
        """Handle critical performance issues"""
        try:
            # Notify relevant components
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_CRITICAL_ALERT,
                    content={
                        'pipeline_id': pipeline_id,
                        'alert': alert,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

            # Trigger mitigation actions
            await self._trigger_performance_mitigation(pipeline_id, alert)

        except Exception as e:
            logger.error(f"Critical performance handling failed: {str(e)}")


    async def _notify_alert_status(
            self,
            pipeline_id: str,
            alert_id: str,
            alert: Dict[str, Any]
    ) -> None:
        """Notify about alert status updates"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.MONITORING_ALERT_STATUS,
                content={
                    'pipeline_id': pipeline_id,
                    'alert_id': alert_id,
                    'alert': alert,
                    'timestamp': datetime.now().isoformat()
                }
            )
        )


    async def _handle_prometheus_export(self, message: ProcessingMessage) -> None:
        """Handle export of metrics in Prometheus format"""
        pipeline_id = message.content.get("pipeline_id")
        metrics_filter = message.content.get("filter", {})

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Get metrics based on filter
            metrics = self._filter_metrics(context.collected_metrics, metrics_filter)

            # Convert to Prometheus format
            prometheus_data = await self._export_prometheus_format(metrics)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_EXPORT_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'format': 'prometheus',
                        'data': prometheus_data,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Prometheus export failed: {str(e)}")
            await self._handle_export_error(pipeline_id, 'prometheus', str(e))


    async def _handle_influxdb_export(self, message: ProcessingMessage) -> None:
        """Handle export of metrics in InfluxDB line protocol format"""
        pipeline_id = message.content.get("pipeline_id")
        metrics_filter = message.content.get("filter", {})

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Get metrics based on filter
            metrics = self._filter_metrics(context.collected_metrics, metrics_filter)

            # Convert to InfluxDB format
            influxdb_data = await self._export_influxdb_format(metrics)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_EXPORT_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'format': 'influxdb',
                        'data': influxdb_data,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"InfluxDB export failed: {str(e)}")
            await self._handle_export_error(pipeline_id, 'influxdb', str(e))


    async def _handle_json_export(self, message: ProcessingMessage) -> None:
        """Handle export of metrics in JSON format"""
        pipeline_id = message.content.get("pipeline_id")
        metrics_filter = message.content.get("filter", {})

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Get metrics based on filter
            metrics = self._filter_metrics(context.collected_metrics, metrics_filter)

            # Convert to JSON format
            json_data = await self._export_json_format(metrics)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_EXPORT_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'format': 'json',
                        'data': json_data,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"JSON export failed: {str(e)}")
            await self._handle_export_error(pipeline_id, 'json', str(e))


    async def _handle_health_status(self, message: ProcessingMessage) -> None:
        """Handle health status updates"""
        pipeline_id = message.content.get("pipeline_id")
        health_status = message.content.get("health_status", {})

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Update context with health status
            context.health_status = health_status
            context.last_health_check = datetime.now()

            # Check for health issues
            if not health_status.get('healthy', False):
                issues = self._analyze_health_issues(health_status)
                if issues:
                    await self._handle_health_alert(
                        ProcessingMessage(
                            message_type=MessageType.MONITORING_HEALTH_ALERT,
                            content={
                                'pipeline_id': pipeline_id,
                                'health_data': {
                                    'status': 'unhealthy',
                                    'issues': issues,
                                    'affected_components': health_status.get('components', [])
                                }
                            },
                            source_identifier=self.module_identifier
                        )
                    )

            # Update overall system status
            await self._update_system_health_status(pipeline_id, health_status)

        except Exception as e:
            logger.error(f"Health status handling failed: {str(e)}")


    async def _handle_resource_check(self, message: ProcessingMessage) -> None:
        """Handle resource check requests"""
        pipeline_id = message.content.get("pipeline_id")
        resource_types = message.content.get("resource_types", ["cpu", "memory", "disk"])

        try:
            # Collect resource metrics
            resource_metrics = {}

            for resource_type in resource_types:
                metrics = await self._collect_resource_metrics(resource_type)
                resource_metrics[resource_type] = metrics

            # Check against thresholds
            threshold_breaches = self._check_resource_thresholds(resource_metrics)

            if threshold_breaches:
                # Handle any threshold breaches
                for breach in threshold_breaches:
                    await self._handle_resource_threshold(
                        ProcessingMessage(
                            message_type=MessageType.MONITORING_RESOURCE_THRESHOLD,
                            content={
                                'pipeline_id': pipeline_id,
                                'threshold': breach
                            },
                            source_identifier=self.module_identifier
                        )
                    )

            # Report resource status
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_RESOURCE_STATUS,
                    content={
                        'pipeline_id': pipeline_id,
                        'resources': resource_metrics,
                        'breaches': threshold_breaches,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Resource check failed: {str(e)}")


    # Helper methods

    def _filter_metrics(
            self,
            metrics: Dict[str, Any],
            filter_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Filter metrics based on provided parameters"""
        filtered_metrics = {}

        start_time = filter_params.get('start_time')
        end_time = filter_params.get('end_time')
        metric_types = filter_params.get('metric_types', [])

        for timestamp, metric_data in metrics.items():
            # Time range filter
            if start_time and timestamp < start_time:
                continue
            if end_time and timestamp > end_time:
                continue

            # Metric type filter
            if metric_types:
                filtered_data = {
                    k: v for k, v in metric_data.items()
                    if k in metric_types
                }
                if filtered_data:
                    filtered_metrics[timestamp] = filtered_data
            else:
                filtered_metrics[timestamp] = metric_data

        return filtered_metrics


    async def _handle_export_error(
            self,
            pipeline_id: str,
            export_format: str,
            error: str
    ) -> None:
        """Handle export error cases"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.MONITORING_EXPORT_FAILED,
                content={
                    'pipeline_id': pipeline_id,
                    'format': export_format,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                },
                source_identifier=self.module_identifier
            )
        )


    def _analyze_health_issues(self, health_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze health status for issues"""
        issues = []

        # Check system health
        if system_health := health_status.get('system'):
            for metric, value in system_health.items():
                if not value:  # If unhealthy
                    issues.append({
                        'type': 'system',
                        'component': metric,
                        'severity': 'high',
                        'message': f'System {metric} is unhealthy'
                    })

        # Check component health
        if components := health_status.get('components'):
            for component, status in components.items():
                if not status.get('responsive', True):
                    issues.append({
                        'type': 'component',
                        'component': component,
                        'severity': 'critical',
                        'message': f'Component {component} is unresponsive'
                    })

        # Check resource health
        if resources := health_status.get('resources'):
            for resource, healthy in resources.items():
                if not healthy:
                    issues.append({
                        'type': 'resource',
                        'component': resource,
                        'severity': 'high',
                        'message': f'Resource {resource} is unhealthy'
                    })

        return issues


    async def _collect_resource_metrics(self, resource_type: str) -> Dict[str, Any]:
        """Collect metrics for specific resource type"""
        import psutil

        try:
            if resource_type == "cpu":
                return {
                    'usage_percent': psutil.cpu_percent(interval=1),
                    'count': psutil.cpu_count(),
                    'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                }
            elif resource_type == "memory":
                mem = psutil.virtual_memory()
                return {
                    'total': mem.total,
                    'available': mem.available,
                    'percent': mem.percent,
                    'used': mem.used,
                    'free': mem.free
                }
            elif resource_type == "disk":
                disk = psutil.disk_usage('/')
                return {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                }
            else:
                logger.warning(f"Unsupported resource type: {resource_type}")
                return {}

        except Exception as e:
            logger.error(f"Resource metric collection failed for {resource_type}: {str(e)}")
            return {}


    def _check_resource_thresholds(
            self,
            resource_metrics: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Check resource metrics against thresholds"""
        breaches = []
        thresholds = self.monitoring_thresholds['alert_thresholds']

        for resource_type, metrics in resource_metrics.items():
            if resource_type == "cpu" and 'usage_percent' in metrics:
                if metrics['usage_percent'] >= thresholds['cpu_usage']['critical']:
                    breaches.append({
                        'resource_type': 'cpu',
                        'current_value': metrics['usage_percent'],
                        'threshold': thresholds['cpu_usage']['critical'],
                        'severity': 'critical'
                    })
                elif metrics['usage_percent'] >= thresholds['cpu_usage']['warning']:
                    breaches.append({
                        'resource_type': 'cpu',
                        'current_value': metrics['usage_percent'],
                        'threshold': thresholds['cpu_usage']['warning'],
                        'severity': 'warning'
                    })

            elif resource_type == "memory" and 'percent' in metrics:
                if metrics['percent'] >= thresholds['memory_usage']['critical']:
                    breaches.append({
                        'resource_type': 'memory',
                        'current_value': metrics['percent'],
                        'threshold': thresholds['memory_usage']['critical'],
                        'severity': 'critical'
                    })
                elif metrics['percent'] >= thresholds['memory_usage']['warning']:
                    breaches.append({
                        'resource_type': 'memory',
                        'current_value': metrics['percent'],
                        'threshold': thresholds['memory_usage']['warning'],
                        'severity': 'warning'
                    })

            elif resource_type == "disk" and 'percent' in metrics:
                if metrics['percent'] >= thresholds['disk_space']['critical']:
                    breaches.append({
                        'resource_type': 'disk',
                        'current_value': metrics['percent'],
                        'threshold': thresholds['disk_space']['critical'],
                        'severity': 'critical'
                    })
                elif metrics['percent'] >= thresholds['disk_space']['warning']:
                    breaches.append({
                        'resource_type': 'disk',
                        'current_value': metrics['percent'],
                        'threshold': thresholds['disk_space']['warning'],
                        'severity': 'warning'
                    })

        return breaches