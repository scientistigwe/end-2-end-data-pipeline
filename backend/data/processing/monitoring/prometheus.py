#
import logging
from typing import Dict, Any
from prometheus_client import start_http_server, Gauge, Counter, Summary

logger = logging.getLogger(__name__)


class PrometheusExporter:
    """
    Prometheus Metrics Monitoring and Exposition

    Responsibilities:
    - Expose system and application metrics
    - Create Prometheus metric collectors
    - Manage metric registration and updates
    """

    def __init__(self, port: int = 8000):
        """
        Initialize Prometheus metrics exposition server

        Args:
            port: HTTP server port for metric exposition
        """
        self.port = port
        self._metrics = {
            'gauges': {},
            'counters': {},
            'summaries': {}
        }
        self._start_exposition_server()

    def _start_exposition_server(self) -> None:
        """
        Start Prometheus HTTP server for metric exposition
        """
        try:
            start_http_server(self.port)
            logger.info(f"Prometheus metrics server started on port {self.port}")
        except Exception as e:
            logger.error(f"Could not start Prometheus server: {e}")

    def export(self, metrics: Dict[str, Any]) -> None:
        """
        Export metrics to Prometheus collectors

        Args:
            metrics: Comprehensive metrics dictionary
        """
        try:
            self._update_metrics(metrics.get('metrics', {}))
        except Exception as e:
            logger.error(f"Metrics export to Prometheus failed: {e}")

    def _update_metrics(self, metrics_data: Dict[str, Any]) -> None:
        """
        Update Prometheus metric collectors

        Args:
            metrics_data: Processed metrics dictionary
        """
        for category, data in metrics_data.items():
            for metric_name, value in data.items():
                # Determine metric type and create/update accordingly
                if isinstance(value, (int, float)):
                    full_metric_name = f"{category}_{metric_name}"

                    # Create gauge if not exists
                    if full_metric_name not in self._metrics['gauges']:
                        self._metrics['gauges'][full_metric_name] = Gauge(
                            full_metric_name,
                            f"Metric for {full_metric_name}"
                        )

                    # Update gauge value
                    self._metrics['gauges'][full_metric_name].set(value)

    def add_custom_metric(
            self,
            name: str,
            description: str,
            metric_type: str = 'gauge'
    ):
        """
        Register a custom Prometheus metric

        Args:
            name: Metric name
            description: Metric description
            metric_type: Type of metric (gauge, counter, summary)
        """
        metric_types = {
            'gauge': Gauge,
            'counter': Counter,
            'summary': Summary
        }

        if metric_type not in metric_types:
            raise ValueError(f"Unsupported metric type: {metric_type}")

        if name not in self._metrics[f"{metric_type}s"]:
            self._metrics[f"{metric_type}s"][name] = metric_types[metric_type](name, description)