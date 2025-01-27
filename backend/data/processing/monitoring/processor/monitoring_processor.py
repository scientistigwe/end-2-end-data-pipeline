import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    ModuleIdentifier,
    ComponentType,
    MonitoringState,
    AlertSeverity,
    MetricType
)

from ..collectors import metric_collector, log_collector
from ..exporters import prometheus_exporter, influxdb_exporter, json_exporter
from ..analyzers import (
    performance_analyzer,
    resource_analyzer,
    anomaly_detector,
    threshold_validator
)

logger = logging.getLogger(__name__)

class MonitoringProcessor:
    """
    Processor for monitoring operations.
    Handles direct interaction with monitoring modules and modules.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        self.module_identifier = ModuleIdentifier(
            component_name="monitoring_processor",
            component_type=ComponentType.MONITORING_PROCESSOR,
            department="monitoring",
            role="processor"
        )

        # Active monitoring tasks
        self.active_tasks: Dict[str, Dict[str, Any]] = {}

        # Initialize collectors
        self.metric_collector = metric_collector
        self.log_collector = log_collector
        self.performance_analyzer = performance_analyzer
        self.resource_analyzer = resource_analyzer
        self.anomaly_detector = anomaly_detector
        self.threshold_validator = threshold_validator

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup message handlers"""
        handlers = {
            MessageType.MONITORING_PROCESSOR_START: self._handle_start_monitoring,
            MessageType.MONITORING_PROCESSOR_STOP: self._handle_stop_monitoring,
            MessageType.MONITORING_PROCESSOR_COLLECT: self._handle_collect_metrics,
            MessageType.MONITORING_PROCESSOR_ANALYZE: self._handle_analyze_metrics,
            MessageType.MONITORING_PROCESSOR_EXPORT: self._handle_export_metrics
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                f"monitoring.{message_type.value}",
                handler
            )

    async def _handle_start_monitoring(self, message: ProcessingMessage) -> None:
        """Handle start monitoring request"""
        try:
            pipeline_id = message.content['pipeline_id']
            config = message.content.get('config', {})

            # Initialize task configuration
            task_config = {
                'metric_types': config.get('metric_types', []),
                'collectors': config.get('collectors', []),
                'interval': config.get('interval', 60),
                'thresholds': config.get('thresholds', {}),
                'correlation_id': message.metadata.correlation_id,
                'collected_metrics': {},
                'active_alerts': []
            }

            self.active_tasks[pipeline_id] = task_config

            # Start initial collection
            await self._collect_metrics(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to start monitoring: {str(e)}")
            await self._publish_error(message, str(e))

    async def _collect_metrics(self, pipeline_id: str) -> None:
        """Collect metrics using configured collectors"""
        task = self.active_tasks.get(pipeline_id)
        if not task:
            return

        try:
            collected_metrics = {}

            # Collect from enabled collectors
            for collector in task['collectors']:
                if collector == 'metrics':
                    metrics = await self.metric_collector.collect(task['metric_types'])
                    collected_metrics['metrics'] = metrics
                elif collector == 'logs':
                    logs = await self.log_collector.collect(task['metric_types'])
                    collected_metrics['logs'] = logs

            task['collected_metrics'] = collected_metrics

            # Analyze collected metrics
            await self._analyze_metrics(pipeline_id, collected_metrics)

            # Publish collected metrics
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_METRICS_COLLECTED,
                    content={
                        'pipeline_id': pipeline_id,
                        'metrics': collected_metrics,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=task['correlation_id'],
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Metrics collection failed: {str(e)}")
            await self._publish_error(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESSOR_COLLECT,
                    content={'pipeline_id': pipeline_id}
                ),
                str(e)
            )

    async def _analyze_metrics(self, pipeline_id: str, metrics: Dict[str, Any]) -> None:
        """Analyze collected metrics"""
        task = self.active_tasks.get(pipeline_id)
        if not task:
            return

        try:
            # Analyze performance metrics
            performance_metrics = await self.performance_analyzer.analyze(
                metrics.get(MetricType.PERFORMANCE.value, {})
            )

            # Analyze resource usage
            resource_metrics = await self.resource_analyzer.analyze(
                metrics.get(MetricType.RESOURCE.value, {})
            )

            # Check for anomalies
            anomalies = await self.anomaly_detector.detect(
                metrics,
                task.get('historical_metrics', [])
            )

            # Validate against thresholds
            violations = await self.threshold_validator.validate(
                metrics,
                task.get('thresholds', {})
            )

            # Generate alerts if needed
            if anomalies or violations:
                await self._generate_alerts(pipeline_id, anomalies, violations)

            # Store analysis results
            task['analysis_results'] = {
                'performance': performance_metrics,
                'resources': resource_metrics,
                'anomalies': anomalies,
                'violations': violations
            }

        except Exception as e:
            logger.error(f"Metrics analysis failed: {str(e)}")
            await self._publish_error(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESSOR_ANALYZE,
                    content={'pipeline_id': pipeline_id}
                ),
                str(e)
            )

    async def _generate_alerts(
            self,
            pipeline_id: str,
            anomalies: List[Dict[str, Any]],
            violations: List[Dict[str, Any]]
    ) -> None:
        """Generate alerts from anomalies and violations"""
        task = self.active_tasks.get(pipeline_id)
        if not task:
            return

        try:
            # Generate anomaly alerts
            for anomaly in anomalies:
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.MONITORING_ALERT_DETECTED,
                        content={
                            'pipeline_id': pipeline_id,
                            'alert': {
                                'type': 'anomaly',
                                'severity': AlertSeverity.HIGH.value,
                                'description': anomaly['description'],
                                'details': anomaly,
                                'timestamp': datetime.now().isoformat()
                            }
                        },
                        metadata=MessageMetadata(
                            correlation_id=task['correlation_id'],
                            source_component=self.module_identifier.component_name,
                            target_component="monitoring_handler"
                        ),
                        source_identifier=self.module_identifier
                    )
                )

            # Generate violation alerts
            for violation in violations:
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.MONITORING_ALERT_DETECTED,
                        content={
                            'pipeline_id': pipeline_id,
                            'alert': {
                                'type': 'violation',
                                'severity': AlertSeverity.CRITICAL.value,
                                'description': violation['description'],
                                'details': violation,
                                'timestamp': datetime.now().isoformat()
                            }
                        },
                        metadata=MessageMetadata(
                            correlation_id=task['correlation_id'],
                            source_component=self.module_identifier.component_name,
                            target_component="monitoring_handler"
                        ),
                        source_identifier=self.module_identifier
                    )
                )

        except Exception as e:
            logger.error(f"Alert generation failed: {str(e)}")
            await self._publish_error(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESSOR_ANALYZE,
                    content={'pipeline_id': pipeline_id}
                ),
                str(e)
            )

    async def _handle_stop_monitoring(self, message: ProcessingMessage) -> None:
        """Handle stop monitoring request"""
        pipeline_id = message.content['pipeline_id']

        if pipeline_id in self.active_tasks:
            # Export final metrics if needed
            await self._export_final_metrics(pipeline_id)

            # Cleanup
            del self.active_tasks[pipeline_id]

    async def _export_final_metrics(self, pipeline_id: str) -> None:
        """Export final metrics before cleanup"""
        task = self.active_tasks.get(pipeline_id)
        if not task:
            return

        try:
            metrics = task.get('collected_metrics', {})

            # Export to configured targets
            for target in task.get('export_targets', []):
                try:
                    if target == 'prometheus':
                        await prometheus_exporter.export(metrics)
                    elif target == 'influxdb':
                        await influxdb_exporter.export(metrics)
                    elif target == 'json':
                        await json_exporter.export(metrics)
                except Exception as export_error:
                    logger.error(f"Export to {target} failed: {str(export_error)}")

        except Exception as e:
            logger.error(f"Final metrics export failed: {str(e)}")

    async def _publish_error(self, message: ProcessingMessage, error: str) -> None:
        """Publish processor error"""
        pipeline_id = message.content.get('pipeline_id')
        if not pipeline_id:
            return

        task = self.active_tasks.get(pipeline_id)
        correlation_id = task['correlation_id'] if task else str(uuid.uuid4())

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.MONITORING_PROCESSOR_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="monitoring_handler"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def cleanup(self) -> None:
        """Cleanup processor resources"""
        try:
            # Export final metrics and cleanup for all tasks
            for pipeline_id in list(self.active_tasks.keys()):
                await self._export_final_metrics(pipeline_id)
                del self.active_tasks[pipeline_id]

        except Exception as e:
            logger.error(f"Processor cleanup failed: {str(e)}")
            raise