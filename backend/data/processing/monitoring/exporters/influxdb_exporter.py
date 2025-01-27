#
import logging
from typing import Dict, Any, List
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime

logger = logging.getLogger(__name__)

class InfluxDBExporter:
    """
    InfluxDB Metrics Export and Time-Series Management

    Responsibilities:
    - Export system and application metrics
    - Manage time-series data storage
    - Support high-performance metric logging
    """

    def __init__(
        self,
        url: str = 'http://localhost:8086',
        token: str = '',
        org: str = 'default',
        bucket: str = 'monitoring'
    ):
        """
        Initialize InfluxDB connection with configurable parameters

        Args:
            url: InfluxDB server URL
            token: Authentication token
            org: Organization name
            bucket: Storage bucket name
        """
        try:
            self.client = InfluxDBClient(url=url, token=token, org=org)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.org = org
            self.bucket = bucket
        except Exception as e:
            logger.error(f"InfluxDB connection error: {e}")
            raise

    def export(self, metrics: Dict[str, Any]) -> None:
        """
        Export metrics to InfluxDB time-series database

        Args:
            metrics: Comprehensive metrics dictionary
        """
        try:
            points = self._create_points(metrics)
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
            logger.info(f"Exported {len(points)} metrics points")
        except Exception as e:
            logger.error(f"Metrics export to InfluxDB failed: {e}")

    def _create_points(self, metrics: Dict[str, Any]) -> List[Point]:
        """
        Transform metrics into InfluxDB data points

        Args:
            metrics: Raw metrics dictionary

        Returns:
            List of InfluxDB data points
        """
        points = []
        timestamp = datetime.now()

        for category, data in metrics.get('metrics', {}).items():
            for metric_name, value in data.items():
                point = (Point(category)
                    .tag('metric', metric_name)
                    .field('value', float(value) if isinstance(value, (int, float)) else 0)
                    .time(timestamp)
                )
                points.append(point)

        return points

    def query(
        self,
        query: str,
        time_range: str = '-1h'
    ) -> List[Dict[str, Any]]:
        """
        Execute custom InfluxDB query

        Args:
            query: InfluxQL or Flux query
            time_range: Time window for query

        Returns:
            Query results
        """
        try:
            query_api = self.client.query_api()
            result = query_api.query(f'from(bucket:"{self.bucket}") {query} range(start: {time_range})')
            return [record.values for record in result]
        except Exception as e:
            logger.error(f"InfluxDB query error: {e}")
            return []

    def close(self) -> None:
        """Close InfluxDB client connection"""
        self.client.close()