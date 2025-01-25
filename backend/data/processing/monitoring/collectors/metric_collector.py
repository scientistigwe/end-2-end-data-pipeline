# backend/data/processing/monitoring/collectors/metric_collector.py
import logging
import psutil
import platform
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Comprehensive System and Application Metric Collection

    Collects detailed metrics about system resources,
    application performance, and runtime characteristics.
    """

    def async_collect(
            self,
            metrics_types: Optional[List[str]] = None,
            pipeline_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Asynchronously collect system and application metrics

        Args:
            metrics_types: Specific metrics to collect
            pipeline_id: Optional pipeline identifier

        Returns:
            Comprehensive metrics dictionary
        """
        try:
            # Default metrics if none specified
            if not metrics_types:
                metrics_types = [
                    'system_resources',
                    'cpu_details',
                    'memory_details',
                    'disk_details',
                    'network_details'
                ]

            metrics = {
                'collection_id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'pipeline_id': pipeline_id,
                'metrics': {}
            }

            # Collect specified metrics
            for metric_type in metrics_types:
                collector_method = getattr(self, f'_collect_{metric_type}', None)
                if collector_method:
                    metrics['metrics'][metric_type] = collector_method()

            return metrics

        except Exception as e:
            logger.error(f"Metrics collection error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _collect_system_resources(self) -> Dict[str, Any]:
        """Collect basic system resource information"""
        return {
            'os': platform.system(),
            'os_release': platform.release(),
            'architecture': platform.machine(),
            'hostname': platform.node()
        }

    def _collect_cpu_details(self) -> Dict[str, Any]:
        """Collect detailed CPU metrics"""
        return {
            'count': psutil.cpu_count(),
            'usage_percent': psutil.cpu_percent(interval=1),
            'logical_cores': psutil.cpu_count(logical=True),
            'frequency': psutil.cpu_freq()._asdict()
        }

    def _collect_memory_details(self) -> Dict[str, Any]:
        """Collect memory usage metrics"""
        memory = psutil.virtual_memory()
        return {
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'percent': memory.percent,
            'swap': dict(psutil.swap_memory()._asdict())
        }

    def _collect_disk_details(self) -> Dict[str, Any]:
        """Collect disk usage metrics"""
        partitions = psutil.disk_partitions()
        disk_metrics = {}

        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_metrics[partition.mountpoint] = {
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                }
            except Exception as e:
                logger.warning(f"Could not get disk metrics for {partition.mountpoint}: {e}")

        return disk_metrics

    def _collect_network_details(self) -> Dict[str, Any]:
        """Collect network interface metrics"""
        return dict(psutil.net_io_counters()._asdict())


metric_collector = MetricsCollector()
