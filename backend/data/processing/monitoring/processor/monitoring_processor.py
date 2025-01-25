import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.messaging.broker import MessageBroker
from core.staging.staging_manager import StagingManager

# Comprehensive import of monitoring modules
import data.processing.monitoring.collectors as collectors
import data.processing.monitoring.alerts.alert_manager as alert_manager
import data.processing.monitoring.metrics_manager as metrics_manager
import data.processing.monitoring.performance_tracker as performance_tracker
import data.processing.monitoring.process as process_monitor
import data.processing.monitoring.prometheus as prometheus
import data.processing.monitoring.influxdb as influxdb
import data.processing.monitoring.json_exporter as json_exporter
import data.processing.monitoring.resource as resource_monitor
import data.processing.monitoring.types as monitoring_types

logger = logging.getLogger(__name__)


class MonitoringProcessor:
    """
    Comprehensive Monitoring Processor for Integrated System Monitoring

    Responsibilities:
    - Coordinate multiple monitoring components
    - Collect and process metrics from various sources
    - Manage system alerts and performance tracking
    - Export monitoring data
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager
    ):
        # Core monitoring components
        self.metrics_manager = metrics_manager.MetricsManager()
        self.alert_manager = alert_manager.AlertManager()
        self.performance_tracker = performance_tracker.PerformanceTracker()
        self.process_monitor = process_monitor.ProcessMonitor()
        self.resource_monitor = resource_monitor.ResourceMonitor()

        # Data exporters
        self.prometheus_exporter = prometheus.PrometheusExporter()
        self.influxdb_exporter = influxdb.InfluxDBExporter()
        self.json_exporter = json_exporter.JSONExporter()

        # Collectors
        self.collectors = {
            'log': collectors.log_collector,
            'metric': collectors.metric_collector
        }

        # Messaging components
        self.message_broker = message_broker
        self.staging_manager = staging_manager

    async def handle_component_request(
            self,
            pipeline_id: str,
            source: str,
            request_content: Dict[str, Any],
            context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process comprehensive monitoring request across multiple collectors

        Args:
            pipeline_id: Unique pipeline identifier
            source: Request source
            request_content: Monitoring request details
            context: Additional contextual information

        Returns:
            Processed monitoring request with collected metrics
        """
        try:
            # Extract monitoring specifications
            metrics_types = request_content.get('metrics_types', [])
            collectors_requested = request_content.get('collectors', list(self.collectors.keys()))

            # Collect metrics from specified collectors
            collected_metrics = {}
            for collector_name in collectors_requested:
                if collector_name in self.collectors:
                    try:
                        collector_metrics = await self.collectors[collector_name].collect(
                            metrics_types=metrics_types,
                            pipeline_id=pipeline_id
                        )
                        collected_metrics[collector_name] = collector_metrics
                    except Exception as e:
                        logger.warning(f"Collector {collector_name} failed: {str(e)}")

            # Record metrics through metrics manager
            self.metrics_manager.record_metrics(
                pipeline_id=pipeline_id,
                metrics=collected_metrics
            )

            return {
                'request_id': str(uuid.uuid4()),
                'pipeline_id': pipeline_id,
                'metrics_types': metrics_types,
                'collected_metrics': collected_metrics,
                'requires_confirmation': False
            }

        except Exception as e:
            logger.error(f"Monitoring request processing failed: {str(e)}")
            raise

    async def process_metrics(
            self,
            pipeline_id: str,
            metrics_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comprehensive metrics processing workflow

        Args:
            pipeline_id: Unique pipeline identifier
            metrics_data: Collected metrics

        Returns:
            Processed metrics with validation and anomaly information
        """
        try:
            # Performance tracking
            self.performance_tracker.record_metrics(pipeline_id, metrics_data)

            # Anomaly detection
            anomalies = self.resource_monitor.detect_anomalies(metrics_data)

            # Export metrics to different systems
            self.prometheus_exporter.export(metrics_data)
            self.influxdb_exporter.export(metrics_data)
            self.json_exporter.export(metrics_data)

            return {
                'metrics_id': str(uuid.uuid4()),
                'pipeline_id': pipeline_id,
                'validated': True,
                'anomalies': anomalies,
                'exported': True,
                'metadata': {
                    'timestamp': datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Metrics processing failed: {str(e)}")
            raise

    async def process_system_alert(
            self,
            pipeline_id: Optional[str],
            alert_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comprehensive system alert processing

        Args:
            pipeline_id: Optional pipeline identifier
            alert_details: Detailed alert information

        Returns:
            Processed alert with additional context
        """
        try:
            # Process alert through alert manager
            processed_alert = self.alert_manager.process_alert(
                pipeline_id=pipeline_id,
                alert_details=alert_details
            )

            # Log and export alert
            self.process_monitor.log_alert(processed_alert)

            return processed_alert

        except Exception as e:
            logger.error(f"Alert processing failed: {str(e)}")
            raise

    async def cleanup(self) -> None:
        """
        Comprehensive cleanup of monitoring resources
        """
        try:
            self.metrics_manager.finalize()
            self.performance_tracker.finalize()
            self.process_monitor.cleanup()
            self.resource_monitor.cleanup()
            self.alert_manager.clear_processed_alerts()

        except Exception as e:
            logger.error(f"Monitoring processor cleanup failed: {str(e)}")
            raise