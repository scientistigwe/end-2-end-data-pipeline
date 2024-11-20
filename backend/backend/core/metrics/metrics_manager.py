from typing import Dict, Any, Optional, Union, List
import threading
from datetime import datetime, timedelta


class MetricsManager:
    """
    Enhanced metrics management system with thread-safe operations,
    historical tracking, and backward compatibility
    """

    def __init__(self):
        """Initialize metrics tracking structures"""
        self._metrics: Dict[str, Any] = {}
        self._historical_metrics: Dict[str, List[tuple[datetime, float]]] = {}
        self._lock = threading.Lock()
        self._retention_period: timedelta = timedelta(hours=24)

    def increment(self, metric_name: str, value: float = 1.0) -> float:
        """
        Backward compatible increment method that calls increment_metric

        Args:
            metric_name (str): Name of the metric
            value (float, optional): Value to increment. Defaults to 1.0.

        Returns:
            float: Updated metric value
        """
        return self.increment_metric(metric_name, value)

    def increment_metric(self, metric_name: str, value: float = 1.0) -> float:
        """
        Increment a metric with historical tracking

        Args:
            metric_name (str): Name of the metric
            value (float, optional): Value to increment. Defaults to 1.0.

        Returns:
            float: Updated metric value
        """
        with self._lock:
            current_value = self._metrics.get(metric_name, 0.0)
            updated_value = current_value + value
            self._metrics[metric_name] = updated_value

            # Track historical data
            if metric_name not in self._historical_metrics:
                self._historical_metrics[metric_name] = []
            self._historical_metrics[metric_name].append((datetime.now(), updated_value))

            # Cleanup old historical data
            self._cleanup_historical_data(metric_name)

            return updated_value

    def update_average_metric(
            self,
            metric_name: str,
            new_value: float,
            total_count: int,
            initial_value: float = 1.0
    ) -> float:
        """
        Update a running average metric with historical tracking

        Args:
            metric_name (str): Name of the metric
            new_value (float): New value to incorporate
            total_count (int): Total number of items
            initial_value (float, optional): Initial default value. Defaults to 1.0.

        Returns:
            float: Updated average metric value
        """
        with self._lock:
            current_value = self._metrics.get(metric_name, initial_value)
            updated_value = (
                    (current_value * (total_count - 1) / total_count) +
                    (new_value / total_count)
            )
            self._metrics[metric_name] = updated_value

            # Track historical data
            if metric_name not in self._historical_metrics:
                self._historical_metrics[metric_name] = []
            self._historical_metrics[metric_name].append((datetime.now(), updated_value))

            # Cleanup old historical data
            self._cleanup_historical_data(metric_name)

            return updated_value

    def get_metric(self, metric_name: str, default: Any = None) -> Any:
        """
        Retrieve current metric value

        Args:
            metric_name (str): Name of the metric
            default (Any, optional): Default value if metric not found

        Returns:
            Any: Metric value or default
        """
        with self._lock:
            return self._metrics.get(metric_name, default)

    def get_metric_history(
            self,
            metric_name: str,
            time_window: Optional[timedelta] = None
    ) -> List[tuple[datetime, float]]:
        """
        Get historical values for a metric

        Args:
            metric_name (str): Name of the metric
            time_window (Optional[timedelta]): Time window to retrieve history for

        Returns:
            List[tuple[datetime, float]]: List of (timestamp, value) pairs
        """
        with self._lock:
            if metric_name not in self._historical_metrics:
                return []

            if time_window is None:
                return list(self._historical_metrics[metric_name])

            cutoff_time = datetime.now() - time_window
            return [
                (ts, val) for ts, val in self._historical_metrics[metric_name]
                if ts >= cutoff_time
            ]

    def reset_metric(self, metric_name: str) -> None:
        """
        Reset a specific metric and its history

        Args:
            metric_name (str): Name of the metric to reset
        """
        with self._lock:
            self._metrics[metric_name] = 0.0
            if metric_name in self._historical_metrics:
                self._historical_metrics[metric_name] = []

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all current metrics

        Returns:
            Dict[str, Any]: Dictionary of all metrics
        """
        with self._lock:
            return dict(self._metrics)

    def set_retention_period(self, hours: int) -> None:
        """
        Set the retention period for historical data

        Args:
            hours (int): Number of hours to retain historical data
        """
        self._retention_period = timedelta(hours=hours)

    def _cleanup_historical_data(self, metric_name: str) -> None:
        """
        Clean up historical data beyond retention period

        Args:
            metric_name (str): Name of the metric to clean up
        """
        if metric_name not in self._historical_metrics:
            return

        cutoff_time = datetime.now() - self._retention_period
        self._historical_metrics[metric_name] = [
            (ts, val) for ts, val in self._historical_metrics[metric_name]
            if ts >= cutoff_time
        ]